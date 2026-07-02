package com.xhs.mobile.app.share

import android.content.ClipData
import android.content.ClipboardManager
import android.content.Context
import android.content.Intent
import android.net.Uri
import android.widget.Toast
import androidx.core.content.FileProvider
import com.xhs.mobile.app.data.PostManifest
import com.xhs.mobile.app.util.Assets

/**
 * 分享到小红书 / 微信。主路径是原生系统分享 Intent（用户手动确认，规避风控）；
 * scheme 深链作为 best-effort 可选项。
 *
 * 诚实边界：微信公众号无可靠第三方 scheme 直达草稿编辑器，走「复制正文 + 打开微信」兜底。
 */
object ShareHelper {

    private const val XHS_PACKAGE = "com.xingin.xhs"
    private const val WECHAT_PACKAGE = "com.tencent.mm"

    // ---------- 小红书 ----------

    // 主路径: ACTION_SEND_MULTIPLE + 图片 content URI + 文本 -> 系统分享面板选小红书。
    // 使用 "* / *" MIME 类型确保图文都被接收方识别 ("image/ *" 会导致小红书忽略 EXTRA_TEXT).
    fun shareToXhs(context: Context, post: PostManifest) {
        val imageUris = materializeCardImages(context, post)
        val text = buildShareText(post)

        // 同时将文本复制到剪贴板作为兜底（部分 App 版本可能仍忽略 EXTRA_TEXT）
        val clipboard = context.getSystemService(Context.CLIPBOARD_SERVICE) as ClipboardManager
        clipboard.setPrimaryClip(ClipData.newPlainText("小红书文案", text))

        val intent = if (imageUris.isNotEmpty()) {
            Intent(Intent.ACTION_SEND_MULTIPLE).apply {
                // 使用 "*/*" 而非 "image/*"——后者会导致小红书只读图片忽略文字
                type = "*/*"
                putParcelableArrayListExtra(Intent.EXTRA_STREAM, ArrayList(imageUris))
                putExtra(Intent.EXTRA_TEXT, text)
            }
        } else {
            Intent(Intent.ACTION_SEND).apply {
                type = "text/plain"
                putExtra(Intent.EXTRA_TEXT, text)
            }
        }
        intent.addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION)

        val chooser = Intent.createChooser(intent, "分享到小红书").apply {
            addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
        }
        if (chooser.resolveActivity(context.packageManager) != null) {
            context.startActivity(chooser)
            Toast.makeText(context, "如文字未带入，请长按粘贴（已复制到剪贴板）", Toast.LENGTH_LONG).show()
        } else {
            Toast.makeText(context, "没有可分享的应用", Toast.LENGTH_SHORT).show()
            tryXhsScheme(context)
        }
    }

    /** 可选：尝试用 scheme 拉起小红书 App（best-effort，失败静默）。 */
    fun tryXhsScheme(context: Context) {
        runCatching {
            val intent = Intent(Intent.ACTION_VIEW, Uri.parse("xhsdiscover://item")).apply {
                addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
            }
            if (intent.resolveActivity(context.packageManager) != null) {
                context.startActivity(intent)
            }
        }
    }

    // ---------- 微信 / 公众号 ----------

    // 发到微信 (聊天/收藏/朋友圈): 多图用 SEND_MULTIPLE, 单图用 SEND。
    // 使用 "* / *" MIME 类型确保图文都被接收方识别。
    fun shareToWechat(context: Context, post: PostManifest) {
        val imageUris = materializeCardImages(context, post)
        val text = buildShareText(post)

        // 兜底：文本也复制到剪贴板
        val clipboard = context.getSystemService(Context.CLIPBOARD_SERVICE) as ClipboardManager
        clipboard.setPrimaryClip(ClipData.newPlainText("分享文案", text))

        val intent = when {
            imageUris.size > 1 -> Intent(Intent.ACTION_SEND_MULTIPLE).apply {
                type = "*/*"
                putParcelableArrayListExtra(Intent.EXTRA_STREAM, ArrayList(imageUris))
                putExtra(Intent.EXTRA_TEXT, text)
            }
            imageUris.size == 1 -> Intent(Intent.ACTION_SEND).apply {
                type = "*/*"
                putExtra(Intent.EXTRA_STREAM, imageUris.first())
                putExtra(Intent.EXTRA_TEXT, text)
            }
            else -> Intent(Intent.ACTION_SEND).apply {
                type = "text/plain"
                putExtra(Intent.EXTRA_TEXT, text)
            }
        }
        intent.setPackage(WECHAT_PACKAGE)
        intent.addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION)
        launchOrFallback(context, intent, "未安装微信，改用系统分享") {
            intent.setPackage(null)
            context.startActivity(Intent.createChooser(intent, "发送到微信").apply {
                addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
            })
        }
    }

    /**
     * 发送到公众号：第三方 App 无可靠 scheme 直达草稿编辑器。
     * 兜底策略：
     * 1. 把正文 HTML 复制到剪贴板。
     * 2. 把卡片图保存到系统 Pictures 目录（用户可在公众号编辑器里手动插入）。
     * 3. 打开微信 App（com.tencent.mm）——公众号编辑通过微信内的「订阅号」入口完成。
     * 4. 同时也提供打开浏览器 mp.weixin.qq.com 的选项（适合习惯用电脑/网页编辑器的用户）。
     */
    fun sendToWechatOfficial(context: Context, post: PostManifest) {
        // 1. 复制正文到剪贴板
        val html = post.wechatHtmlAssetPath()?.let {
            runCatching { context.assets.open(it).bufferedReader().use { r -> r.readText() } }.getOrNull()
        }
        val title = post.wechat?.title ?: post.title
        val digest = post.wechat?.digest ?: ""
        val payload = buildString {
            appendLine(title)
            if (digest.isNotBlank()) appendLine(digest)
            appendLine()
            appendLine(html ?: post.caption)
        }
        val clipboard = context.getSystemService(Context.CLIPBOARD_SERVICE) as ClipboardManager
        clipboard.setPrimaryClip(ClipData.newPlainText("公众号正文", payload))

        // 2. 把卡片图保存到 Pictures 目录，方便用户在公众号编辑器手动插入
        val savedImageCount = saveImagesToPictures(context, post)

        // 3. 打开微信 App（公众号编辑在微信内通过「订阅号」入口完成）
        val wechatLaunched = launchPackage(context, WECHAT_PACKAGE)

        // 4. 构建提示信息
        val msg = buildString {
            append("正文已复制到剪贴板")
            if (savedImageCount > 0) {
                append("，${savedImageCount}张图片已保存到相册")
            }
            append("。")
            if (wechatLaunched) {
                append("请在微信「订阅号」里粘贴发布。")
            } else {
                append("请打开微信「订阅号」或浏览器访问 mp.weixin.qq.com 粘贴发布。")
            }
        }
        Toast.makeText(context, msg, Toast.LENGTH_LONG).show()

        // 5. 如果微信未安装/未拉起，尝试打开浏览器到公众号网页编辑器
        if (!wechatLaunched) {
            openBrowserFallback(context)
        }
    }

    /** 把卡片图从 assets 保存到系统 Pictures/xhs-share/ 目录，便于用户在公众号编辑器手动插入。
     *  Android 10+ 通过 MediaStore 写入（不需要存储权限）；旧版用 direct file + MediaScanner。 */
    private fun saveImagesToPictures(context: Context, post: PostManifest): Int {
        var count = 0
        val displayName = "${post.id}"
        for (card in post.cards) {
            val assetPath = post.cardAssetPath(card)
            val imageName = "${displayName}_${card.index}.png"
            runCatching {
                val values = android.content.ContentValues().apply {
                    put(android.provider.MediaStore.Images.Media.DISPLAY_NAME, imageName)
                    put(android.provider.MediaStore.Images.Media.MIME_TYPE, "image/png")
                    put(android.provider.MediaStore.Images.Media.RELATIVE_PATH,
                        "${android.os.Environment.DIRECTORY_PICTURES}/xhs-share")
                }
                val uri = context.contentResolver.insert(
                    android.provider.MediaStore.Images.Media.EXTERNAL_CONTENT_URI,
                    values
                )
                uri?.let {
                    context.contentResolver.openOutputStream(it)?.use { output ->
                        context.assets.open(assetPath).use { input -> input.copyTo(output) }
                    }
                    count++
                }
            }
        }
        return count
    }

    /** 浏览器兜底：打开 mp.weixin.qq.com（公众号网页编辑器）。 */
    private fun openBrowserFallback(context: Context) {
        runCatching {
            val intent = Intent(Intent.ACTION_VIEW, Uri.parse("https://mp.weixin.qq.com/")).apply {
                addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
            }
            context.startActivity(intent)
        }
    }

    // ---------- 内部工具 ----------

    private fun materializeCardImages(context: Context, post: PostManifest): List<Uri> {
        val uris = mutableListOf<Uri>()
        for (card in post.cards) {
            val assetPath = post.cardAssetPath(card)
            val destName = "${post.id}_${card.index}.png"
            val file = Assets.copyToCache(context, assetPath, destName) ?: continue
            runCatching {
                uris.add(FileProvider.getUriForFile(context, "${context.packageName}.fileprovider", file))
            }
        }
        return uris
    }

    private fun buildShareText(post: PostManifest): String {
        val tags = if (post.tags.isEmpty()) "" else "\n" + post.tags.joinToString(" ") { "#$it" }
        return "${post.title}\n\n${post.caption}$tags"
    }

    private fun launchPackage(context: Context, pkg: String): Boolean {
        return runCatching {
            val intent = context.packageManager.getLaunchIntentForPackage(pkg)
            if (intent != null) {
                intent.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
                context.startActivity(intent)
                true
            } else false
        }.getOrDefault(false)
    }

    private fun launchOrFallback(
        context: Context,
        intent: Intent,
        fallbackToast: String,
        fallback: () -> Unit
    ) {
        runCatching {
            intent.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
            context.startActivity(intent)
        }.onFailure {
            Toast.makeText(context, fallbackToast, Toast.LENGTH_SHORT).show()
            fallback()
        }
    }
}
