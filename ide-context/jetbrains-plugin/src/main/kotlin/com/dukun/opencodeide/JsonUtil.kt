package com.dukun.opencodeide

object JsonUtil {
    private fun escape(value: String): String {
        val builder = StringBuilder(value.length + 16)
        value.forEach { ch ->
            when (ch) {
                '\\' -> builder.append("\\\\")
                '"' -> builder.append("\\\"")
                '\b' -> builder.append("\\b")
                '\u000C' -> builder.append("\\f")
                '\n' -> builder.append("\\n")
                '\r' -> builder.append("\\r")
                '\t' -> builder.append("\\t")
                else -> {
                    if (ch.code < 0x20) {
                        builder.append("\\u%04x".format(ch.code))
                    } else {
                        builder.append(ch)
                    }
                }
            }
        }
        return builder.toString()
    }

    private fun quoteOrNull(value: String?): String {
        return if (value == null) "null" else "\"${escape(value)}\""
    }

    private fun intOrNull(value: Int?): String {
        return value?.toString() ?: "null"
    }

    private fun listOfStrings(values: List<String>): String {
        return values.joinToString(prefix = "[", postfix = "]") { "\"${escape(it)}\"" }
    }

    fun toJson(snapshot: IdeContextSnapshot): String {
        return """
            {
              "contextType": ${quoteOrNull(snapshot.contextType)},
              "workspace": ${quoteOrNull(snapshot.workspace)},
              "filePath": ${quoteOrNull(snapshot.filePath)},
              "className": ${quoteOrNull(snapshot.className)},
              "lineStart": ${intOrNull(snapshot.lineStart)},
              "lineEnd": ${intOrNull(snapshot.lineEnd)},
              "text": ${quoteOrNull(snapshot.text)},
              "truncated": ${snapshot.truncated},
              "updatedAt": ${quoteOrNull(snapshot.updatedAt)},
              "revision": ${snapshot.revision}
            }
        """.trimIndent()
    }

    fun toJson(lock: IdeContextLockRecord): String {
        return """
            {
              "version": ${lock.version},
              "workspaceFolders": ${listOfStrings(lock.workspaceFolders)},
              "ideName": ${quoteOrNull(lock.ideName)},
              "transport": ${quoteOrNull(lock.transport)},
              "url": ${quoteOrNull(lock.url)},
              "authToken": ${quoteOrNull(lock.authToken)},
              "pid": ${lock.pid},
              "updatedAt": ${quoteOrNull(lock.updatedAt)}
            }
        """.trimIndent()
    }
}
