package com.dukun.opencodeide

data class IdeContextSnapshot(
    val contextType: String,
    val workspace: String?,
    val filePath: String?,
    val className: String?,
    val lineStart: Int?,
    val lineEnd: Int?,
    val text: String?,
    val truncated: Boolean,
    val updatedAt: String,
    val revision: Long
)

data class IdeContextLockRecord(
    val version: Int,
    val workspaceFolders: List<String>,
    val ideName: String,
    val transport: String,
    val url: String,
    val authToken: String,
    val pid: Long,
    val updatedAt: String
)
