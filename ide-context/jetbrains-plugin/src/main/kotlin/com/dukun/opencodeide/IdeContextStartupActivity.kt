package com.dukun.opencodeide

import com.intellij.openapi.project.Project
import com.intellij.openapi.startup.ProjectActivity

class IdeContextStartupActivity : ProjectActivity {
    override suspend fun execute(project: Project) {
        project.getService(IdeContextProjectService::class.java).start()
    }
}
