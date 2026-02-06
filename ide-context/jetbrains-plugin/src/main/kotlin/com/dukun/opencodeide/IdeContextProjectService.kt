package com.dukun.opencodeide

import com.intellij.openapi.Disposable
import com.intellij.openapi.application.ApplicationNamesInfo
import com.intellij.openapi.application.ReadAction
import com.intellij.openapi.editor.Editor
import com.intellij.openapi.fileEditor.FileDocumentManager
import com.intellij.openapi.project.Project
import com.intellij.openapi.util.TextRange
import com.intellij.psi.PsiClass
import com.intellij.psi.PsiDocumentManager
import com.intellij.psi.util.PsiTreeUtil
import com.intellij.util.concurrency.AppExecutorUtil
import com.sun.net.httpserver.HttpExchange
import com.sun.net.httpserver.HttpServer
import java.net.InetAddress
import java.net.InetSocketAddress
import java.nio.charset.StandardCharsets
import java.nio.file.Files
import java.nio.file.Path
import java.nio.file.Paths
import java.time.Instant
import java.util.concurrent.Executors
import java.util.concurrent.ScheduledFuture
import java.util.concurrent.TimeUnit
import java.util.concurrent.atomic.AtomicLong
import java.util.concurrent.atomic.AtomicReference
import kotlin.math.max
import kotlin.math.min

class IdeContextProjectService(private val project: Project) : Disposable {

    private val revision = AtomicLong(0)
    private val snapshotRef = AtomicReference(
        IdeContextSnapshot(
            contextType = "none",
            workspace = project.basePath,
            filePath = null,
            className = null,
            lineStart = null,
            lineEnd = null,
            text = null,
            truncated = false,
            updatedAt = Instant.now().toString(),
            revision = 0
        )
    )

    private var started = false
    private var authToken: String = ""
    private var server: HttpServer? = null
    private var tracker: IdeContextSelectionTracker? = null
    private var lockFile: Path? = null
    private var lockHeartbeat: ScheduledFuture<*>? = null

    fun start() {
        if (started) return
        started = true
        authToken = TokenUtil.generateAuthToken()

        val socketAddress = InetSocketAddress(InetAddress.getByName("127.0.0.1"), 0)
        val httpServer = HttpServer.create(socketAddress, 0)
        httpServer.createContext("/health") { exchange ->
            writeResponse(exchange, 200, "{\"ok\":true}")
        }
        httpServer.createContext("/context/current") { exchange ->
            if (exchange.requestMethod != "GET") {
                writeResponse(exchange, 405, "{\"error\":\"method_not_allowed\"}")
                return@createContext
            }
            if (!isAuthorized(exchange)) {
                writeResponse(exchange, 401, "{\"error\":\"unauthorized\"}")
                return@createContext
            }
            writeResponse(exchange, 200, JsonUtil.toJson(snapshotRef.get()))
        }
        httpServer.executor = Executors.newSingleThreadExecutor { runnable ->
            Thread(runnable, "opencode-ide-context-http").apply { isDaemon = true }
        }
        httpServer.start()
        server = httpServer

        writeLockFile()
        tracker = IdeContextSelectionTracker(project, this).also { it.start() }

        lockHeartbeat = AppExecutorUtil.getAppScheduledExecutorService().scheduleWithFixedDelay(
            { writeLockFile() },
            10,
            10,
            TimeUnit.SECONDS
        )
    }

    fun updateFromEditor(editor: Editor) {
        val newSnapshot = ReadAction.compute<IdeContextSnapshot?, RuntimeException> {
            val document = editor.document
            val virtualFile = FileDocumentManager.getInstance().getFile(document) ?: return@compute null
            val filePath = virtualFile.path
            val workspace = project.basePath
            if (!shouldTrackFile(filePath, workspace)) {
                return@compute null
            }

            if (editor.selectionModel.hasSelection()) {
                buildSelectionSnapshot(editor, filePath, workspace)
            } else {
                buildClassFallbackSnapshot(editor, filePath, workspace)
                    ?: buildCaretWindowSnapshot(editor, filePath, workspace)
            }
        } ?: return

        snapshotRef.set(newSnapshot)
    }

    private fun shouldTrackFile(filePath: String, workspace: String?): Boolean {
        // Ignore pseudo files from terminal/output editors.
        if (filePath == "/terminal_output") {
            return false
        }

        if (workspace.isNullOrBlank()) {
            return true
        }

        return try {
            val workspacePath = Paths.get(workspace).toAbsolutePath().normalize()
            val currentPath = Paths.get(filePath).toAbsolutePath().normalize()
            currentPath.startsWith(workspacePath)
        } catch (_: Exception) {
            false
        }
    }

    private fun buildSelectionSnapshot(editor: Editor, filePath: String, workspace: String?): IdeContextSnapshot {
        val selectionModel = editor.selectionModel
        val start = editor.offsetToLogicalPosition(selectionModel.selectionStart)
        val end = editor.offsetToLogicalPosition(selectionModel.selectionEnd)
        val rawText = selectionModel.selectedText ?: ""
        val (text, truncated) = truncate(rawText)

        return IdeContextSnapshot(
            contextType = "selection",
            workspace = workspace,
            filePath = filePath,
            className = null,
            lineStart = start.line + 1,
            lineEnd = max(start.line + 1, end.line + 1),
            text = text,
            truncated = truncated,
            updatedAt = Instant.now().toString(),
            revision = revision.incrementAndGet()
        )
    }

    private fun buildClassFallbackSnapshot(editor: Editor, filePath: String, workspace: String?): IdeContextSnapshot? {
        val document = editor.document
        val psiFile = PsiDocumentManager.getInstance(project).getPsiFile(document) ?: return null
        val caretOffset = editor.caretModel.offset
        val element = psiFile.findElementAt(caretOffset) ?: return null
        val psiClass = PsiTreeUtil.getParentOfType(element, PsiClass::class.java, false) ?: return null
        val range = psiClass.textRange

        val rawText = document.getText(range)
        val (text, truncated) = truncate(rawText)
        val lineStart = document.getLineNumber(range.startOffset) + 1
        val endOffset = max(range.startOffset, range.endOffset - 1)
        val lineEnd = document.getLineNumber(endOffset) + 1

        return IdeContextSnapshot(
            contextType = "class_fallback",
            workspace = workspace,
            filePath = filePath,
            className = psiClass.name,
            lineStart = lineStart,
            lineEnd = lineEnd,
            text = text,
            truncated = truncated,
            updatedAt = Instant.now().toString(),
            revision = revision.incrementAndGet()
        )
    }

    private fun buildCaretWindowSnapshot(editor: Editor, filePath: String, workspace: String?): IdeContextSnapshot {
        val document = editor.document
        val lineCount = max(document.lineCount, 1)
        val caretLine = document.getLineNumber(editor.caretModel.offset) + 1
        val lineStart = max(1, caretLine - CARET_WINDOW_LINES)
        val lineEnd = min(lineCount, caretLine + CARET_WINDOW_LINES)

        val startOffset = document.getLineStartOffset(lineStart - 1)
        val endOffset = document.getLineEndOffset(lineEnd - 1)
        val rawText = document.getText(TextRange(startOffset, endOffset))
        val (text, truncated) = truncate(rawText)

        return IdeContextSnapshot(
            contextType = "caret_window",
            workspace = workspace,
            filePath = filePath,
            className = null,
            lineStart = lineStart,
            lineEnd = lineEnd,
            text = text,
            truncated = truncated,
            updatedAt = Instant.now().toString(),
            revision = revision.incrementAndGet()
        )
    }

    private fun truncate(value: String): Pair<String, Boolean> {
        if (value.length <= MAX_TEXT_CHARS) return value to false
        return value.substring(0, MAX_TEXT_CHARS) to true
    }

    private fun writeLockFile() {
        val httpServer = server ?: return
        val port = httpServer.address.port
        val now = Instant.now().toString()

        val lockDir = lockDirectory()
        Files.createDirectories(lockDir)

        val url = "http://127.0.0.1:$port"
        val workspaceFolders = project.basePath?.let { listOf(it) } ?: emptyList()
        val lock = IdeContextLockRecord(
            version = 1,
            workspaceFolders = workspaceFolders,
            ideName = ApplicationNamesInfo.getInstance().fullProductName,
            transport = "http",
            url = url,
            authToken = authToken,
            pid = ProcessHandle.current().pid(),
            updatedAt = now
        )

        val filePath = lockDir.resolve("$port.lock")
        Files.writeString(filePath, JsonUtil.toJson(lock), StandardCharsets.UTF_8)
        lockFile = filePath
    }

    private fun lockDirectory(): Path {
        val configured = System.getenv("OPENCODE_IDE_LOCK_DIR")
        if (!configured.isNullOrBlank()) {
            return Paths.get(configured)
        }
        return Paths.get(System.getProperty("user.home"), ".opencode", "ide")
    }

    private fun isAuthorized(exchange: HttpExchange): Boolean {
        val header = exchange.requestHeaders.getFirst(HEADER_TOKEN)
        if (header == authToken) return true

        val auth = exchange.requestHeaders.getFirst("Authorization")
        if (auth != null && auth.startsWith("Bearer ")) {
            return auth.removePrefix("Bearer ").trim() == authToken
        }
        return false
    }

    private fun writeResponse(exchange: HttpExchange, statusCode: Int, responseBody: String) {
        val bytes = responseBody.toByteArray(StandardCharsets.UTF_8)
        exchange.responseHeaders.add("Content-Type", "application/json; charset=utf-8")
        exchange.sendResponseHeaders(statusCode, bytes.size.toLong())
        exchange.responseBody.use { output -> output.write(bytes) }
    }

    override fun dispose() {
        lockHeartbeat?.cancel(true)
        lockHeartbeat = null

        tracker?.dispose()
        tracker = null

        server?.stop(0)
        server = null

        lockFile?.let {
            runCatching { Files.deleteIfExists(it) }
        }
        lockFile = null
        started = false
    }

    companion object {
        private const val HEADER_TOKEN = "X-OpenCode-Ide-Authorization"
        private const val MAX_TEXT_CHARS = 8 * 1024
        private const val CARET_WINDOW_LINES = 60
    }
}
