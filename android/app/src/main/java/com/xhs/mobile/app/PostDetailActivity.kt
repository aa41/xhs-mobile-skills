package com.xhs.mobile.app

import android.os.Bundle
import android.view.View
import android.webkit.WebView
import android.widget.Button
import android.widget.TextView
import androidx.appcompat.app.AppCompatActivity
import androidx.core.view.ViewCompat
import androidx.core.view.WindowInsetsCompat
import androidx.viewpager2.widget.ViewPager2
import com.xhs.mobile.app.data.PostManifest
import com.xhs.mobile.app.data.PostRepository
import com.xhs.mobile.app.share.ShareHelper
import com.xhs.mobile.app.ui.XhsCardAdapter
import com.google.android.material.button.MaterialButtonToggleGroup
import kotlin.math.abs

/** 详情：小红书 / 微信公众号 模拟预览 + 分享按钮。 */

class PostDetailActivity : AppCompatActivity() {

    private lateinit var post: PostManifest
    private lateinit var platformTabs: MaterialButtonToggleGroup
    private lateinit var detailTitle: TextView
    private lateinit var detailMeta: TextView

    // 小红书预览
    private lateinit var xhsContainer: View
    private lateinit var viewPager: ViewPager2
    private lateinit var pagerHint: TextView
    private lateinit var xhsTitle: TextView
    private lateinit var xhsCaption: TextView
    private lateinit var xhsTags: TextView

    // 微信公众号预览
    private lateinit var wechatContainer: View
    private lateinit var webView: WebView
    private lateinit var wechatTitle: TextView
    private lateinit var wechatDigest: TextView

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_post_detail)

        // 规避状态栏高度
        applyStatusBarInsets()

        val postId = intent.getStringExtra(EXTRA_POST_ID) ?: run { finish(); return }
        post = PostRepository.findById(this, postId) ?: run { finish(); return }

        title = post.title

        bindViews()
        setupXhsPreview()
        setupWechatPreview()
        setupButtons()
        showPlatform(true)   // 默认小红书
    }

    private fun bindViews() {
        xhsContainer = findViewById(R.id.xhsContainer)
        viewPager = findViewById(R.id.viewPager)
        pagerHint = findViewById(R.id.pagerHint)
        xhsTitle = findViewById(R.id.xhsTitle)
        xhsCaption = findViewById(R.id.xhsCaption)
        xhsTags = findViewById(R.id.xhsTags)

        wechatContainer = findViewById(R.id.wechatContainer)
        webView = findViewById(R.id.webView)
        wechatTitle = findViewById(R.id.wechatTitle)
        wechatDigest = findViewById(R.id.wechatDigest)
        platformTabs = findViewById(R.id.platformTabs)
        detailTitle = findViewById(R.id.detailTitle)
        detailMeta = findViewById(R.id.detailMeta)

        detailTitle.text = post.title
        detailMeta.text = "${post.date}  ·  ${post.cardCount} 张卡片  ·  ${post.roleLabel}"

        findViewById<View>(R.id.btnBack).setOnClickListener { finish() }
        findViewById<View>(R.id.tabXhs).setOnClickListener { showPlatform(true) }
        findViewById<View>(R.id.tabWechat).setOnClickListener { showPlatform(false) }
    }

    private fun setupXhsPreview() {
        xhsTitle.text = post.title
        xhsCaption.text = post.caption
        xhsTags.text = if (post.tags.isEmpty()) "" else post.tags.joinToString("  ") { "#$it" }

        if (post.cards.isNotEmpty()) {
            viewPager.adapter = XhsCardAdapter(this, post, post.cards)
            viewPager.offscreenPageLimit = 1
            viewPager.setPageTransformer { page, position ->
                val distance = 1f - abs(position).coerceAtMost(1f)
                page.alpha = 0.82f + distance * 0.18f
                page.scaleY = 0.96f + distance * 0.04f
            }
            pagerHint.text = "1 / ${post.cards.size}"
            viewPager.registerOnPageChangeCallback(object : ViewPager2.OnPageChangeCallback() {
                override fun onPageSelected(position: Int) {
                    pagerHint.text = "${position + 1} / ${post.cards.size}"
                }
            })
            pagerHint.visibility = View.VISIBLE
        } else {
            pagerHint.visibility = View.GONE
        }
    }

    private fun setupWechatPreview() {
        wechatTitle.text = post.wechat?.title ?: post.title
        wechatDigest.text = post.wechat?.digest ?: ""

        val html = post.wechatHtmlAssetPath()?.let { path ->
            runCatching { assets.open(path).bufferedReader().use { it.readText() } }.getOrNull()
        } ?: run {
            // HTML 转义 caption 文本，防止 XSS 和渲染异常
            val escaped = android.text.TextUtils.htmlEncode(post.caption)
            "<p>${escaped.replace("\n", "<br>")}</p>"
        }

        // 安全配置：禁用 JS、禁用文件访问（只加载本地 assets）
        webView.settings.javaScriptEnabled = false
        webView.settings.allowFileAccess = false
        webView.settings.allowContentAccess = false
        webView.loadDataWithBaseURL("file:///android_asset/", html, "text/html", "utf-8", null)
    }

    private fun setupButtons() {
        findViewById<Button>(R.id.btnShareXhs).setOnClickListener { ShareHelper.shareToXhs(this, post) }
        findViewById<Button>(R.id.btnShareWechat).setOnClickListener { ShareHelper.shareToWechat(this, post) }
        findViewById<Button>(R.id.btnOfficial).setOnClickListener { ShareHelper.sendToWechatOfficial(this, post) }
    }

    private fun showPlatform(xhs: Boolean) {
        xhsContainer.visibility = if (xhs) View.VISIBLE else View.GONE
        wechatContainer.visibility = if (xhs) View.GONE else View.VISIBLE
        platformTabs.check(if (xhs) R.id.tabXhs else R.id.tabWechat)
    }

    /** 给根布局顶部加 status bar 高度 padding，避免内容与状态栏重叠。 */
    private fun applyStatusBarInsets() {
        val header = findViewById<View>(R.id.detailHeader)
        val initialTop = header.paddingTop
        ViewCompat.setOnApplyWindowInsetsListener(header) { view, insets ->
            val statusBarHeight = insets.getInsets(WindowInsetsCompat.Type.statusBars()).top
            view.setPadding(
                view.paddingLeft,
                initialTop + statusBarHeight,
                view.paddingRight,
                view.paddingBottom
            )
            insets
        }
    }

    companion object {
        const val EXTRA_POST_ID = "post_id"
    }
}
