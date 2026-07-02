package com.xhs.mobile.app.util

import android.content.Context
import android.graphics.Bitmap
import android.graphics.BitmapFactory
import java.io.File

/** 从 assets 读图为 Bitmap；以及把 assets 文件拷到缓存目录（用于 FileProvider 分享）。 */

object Assets {

    fun decodeBitmap(context: Context, assetPath: String): Bitmap? {
        return runCatching {
            context.assets.open(assetPath).use { input ->
                BitmapFactory.decodeStream(input)
            }
        }.getOrNull()
    }

    /** 把 assets 下的文件拷到 cacheDir/share/<id>/，返回拷贝后的 File。 */
    fun copyToCache(context: Context, assetPath: String, destName: String): File? {
        return runCatching {
            val outDir = File(context.cacheDir, "share").apply { mkdirs() }
            val outFile = File(outDir, destName)
            context.assets.open(assetPath).use { input ->
                outFile.outputStream().use { output -> input.copyTo(output) }
            }
            outFile
        }.getOrNull()
    }
}
