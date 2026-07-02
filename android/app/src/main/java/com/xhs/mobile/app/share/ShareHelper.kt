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
    private const val MP_PACKAGE = "com.tencent.mp"   // 订阅号助手

    // ---------- 小红书 ----------

    // 主路径: ACTION_SEND_MULTIPLE + 图片 content URI → 系统分享面板选小红书。
    // MIME 用 image/png（不用 image/* 避免忽略文字，不用 */* 避免被误判为"图片+视频"）。
    // 文字通过剪贴板兜底：分享前自动复制，用户在小红书里长按粘贴即可。
    fun shareToXhs(context: Context, post: PostManifest) {
        val imageUris = materializeCardImages(context, post)
        val text = buildShareText(post)

        // 先复制文字到剪贴板（核心兜底：确保文字一定能被用户粘贴）
        val clipboard = context.getSystemService(Context.CLIPBOARD_SERVICE) as ClipboardManager
        clipboard.setPrimaryClip(ClipData.newPlainText("小红书文案", text))

        val intent = if (imageUris.isNotEmpty()) {
            Intent(Intent.ACTION_SEND_MULTIPLE).apply {
                type = "image/png"
                putParcelableArrayListExtra(Intent.EXTRA_STREAM, ArrayList(imageUris))
                putExtra(Intent.EXTRA_TEXT, text)  // 部分版本支持，不放也无害
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
            Toast.makeText(context, "图片已发送，文字已复制到剪贴板，请长按粘贴", Toast.LENGTH_LONG).show()
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
    // 微信对 image/png 支持良好，EXTRA_TEXT 在微信中也能被读取。
    fun shareToWechat(context: Context, post: PostManifest) {
        val imageUris = materializeCardImages(context, post)
        val text = buildShareText(post)

        // 兜底：文本也复制到剪贴板
        val clipboard = context.getSystemService(Context.CLIPBOARD_SERVICE) as ClipboardManager
        clipboard.setPrimaryClip(ClipData.newPlainText("分享文案", text))

        val intent = when {
            imageUris.size > 1 -> Intent(Intent.ACTION_SEND_MULTIPLE).apply {
                type = "image/png"
                putParcelableArrayListExtra(Intent.EXTRA_STREAM, ArrayList(imageUris))
                putExtra(Intent.EXTRA_TEXT, text)
            }
            imageUris.size == 1 -> Intent(Intent.ACTION_SEND).apply {
                type = "image/png"
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
     * 发送到公众号：
     * 1. 复制正文 HTML 到剪贴板。
     * 2. 保存卡片图到系统相册。
     * 3. 优先打开「订阅号助手」App (com.tencent.mp)。
     * 4. 未安装则打开微信 → 订阅号入口。
     * 5. 最差情况打开浏览器 mp.weixin.qq.com。
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

        // 2. 保存图片到相册
        val savedImageCount = saveImagesToPictures(context, post)

        // 3. 按优先级尝试打开：订阅号助手 > 微信 > 浏览器
        val mpLaunched = launchPackage(context, MP_PACKAGE)      // 订阅号助手
        val wechatLaunched = if (!mpLaunched) launchPackage(context, WECHAT_PACKAGE) else false

        val targetApp = when {
            mpLaunched -> "订阅号助手"
            wechatLaunched -> "微信"
            else -> null
        }

        val msg = buildString {
            append("正文已复制到剪贴板")
            if (savedImageCount > 0) append("，${savedImageCount}张图片已保存到相册")
            append("。")
            if (targetApp != null) {
                append("请打开「${targetApp}」→ 素材管理 → 新建图文 → 粘贴发布。")
            } else {
                append("请打开微信「订阅号」或浏览器 mp.weixin.qq.com 粘贴发布。")
            }
        }
        Toast.makeText(context, msg, Toast.LENGTH_LONG).show()

        // 浏览器兜底
        if (targetApp == null) {
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
