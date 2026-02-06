package com.dukun.opencodeide

import com.intellij.openapi.Disposable
import com.intellij.openapi.application.ApplicationManager
import com.intellij.openapi.editor.event.CaretEvent
import com.intellij.openapi.editor.event.CaretListener
import com.intellij.openapi.editor.event.SelectionEvent
import com.intellij.openapi.editor.event.SelectionListener
import com.intellij.openapi.fileEditor.FileEditorManager
import com.intellij.openapi.fileEditor.FileEditorManagerEvent
import com.intellij.openapi.fileEditor.FileEditorManagerListener
import com.intellij.openapi.fileEditor.FileEditorManagerListener.FILE_EDITOR_MANAGER
import com.intellij.openapi.project.Project
import com.intellij.util.messages.MessageBusConnection

class IdeContextSelectionTracker(
    private val project: Project,
    private val service: IdeContextProjectService
) : Disposable {

    private val busConnection: MessageBusConnection = project.messageBus.connect()

    private val selectionListener = object : SelectionListener {
        override fun selectionChanged(event: SelectionEvent) {
            service.updateFromEditor(event.editor)
        }
    }

    private val caretListener = object : CaretListener {
        override fun caretPositionChanged(event: CaretEvent) {
            service.updateFromEditor(event.editor)
        }
    }

    fun start() {
        ApplicationManager.getApplication().invokeLater {
            if (project.isDisposed) return@invokeLater

            val multicaster = com.intellij.openapi.editor.EditorFactory.getInstance().eventMulticaster
            multicaster.addSelectionListener(selectionListener, this)
            multicaster.addCaretListener(caretListener, this)

            busConnection.subscribe(FILE_EDITOR_MANAGER, object : FileEditorManagerListener {
                override fun selectionChanged(event: FileEditorManagerEvent) {
                    (event.newEditor as? com.intellij.openapi.fileEditor.TextEditor)?.let {
                        service.updateFromEditor(it.editor)
                    }
                }
            })

            FileEditorManager.getInstance(project).selectedTextEditor?.let {
                service.updateFromEditor(it)
            }
        }
    }

    override fun dispose() {
        busConnection.dispose()
    }
}
