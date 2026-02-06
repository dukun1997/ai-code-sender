package com.dukun.opencodeide

import java.security.SecureRandom
import java.util.Base64

object TokenUtil {
    private val secureRandom = SecureRandom()

    fun generateAuthToken(): String {
        val bytes = ByteArray(32)
        secureRandom.nextBytes(bytes)
        return Base64.getUrlEncoder().withoutPadding().encodeToString(bytes)
    }
}
