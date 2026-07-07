package com.xhs.mobile.app

import android.content.Intent
import android.os.Bundle
import android.view.View
import android.widget.TextView
import androidx.appcompat.app.AppCompatActivity
import androidx.core.view.ViewCompat
import androidx.core.view.WindowInsetsCompat
import androidx.recyclerview.widget.LinearLayoutManager
import androidx.recyclerview.widget.RecyclerView
import com.xhs.mobile.app.data.PostRepository
import com.xhs.mobile.app.ui.PostListAdapter

/** 首屏：扫描 assets/posts，按日期倒序列出。 */

class MainActivity : AppCompatActivity() {

    private lateinit var recyclerView: RecyclerView
    private lateinit var emptyView: View
    private lateinit var postCount: TextView
    private lateinit var latestDate: TextView

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_main)

        // 规避状态栏高度：给标题区域加顶部 inset
        applyStatusBarInsets()

        recyclerView = findViewById(R.id.recyclerView)
        emptyView = findViewById(R.id.emptyView)
        postCount = findViewById(R.id.postCount)
        latestDate = findViewById(R.id.latestDate)
        recyclerView.layoutManager = LinearLayoutManager(this)

        val posts = PostRepository.loadAll(this)
        postCount.text = "${posts.size} 条内容"
        latestDate.text = posts.firstOrNull()?.date?.let { "最新 $it" } ?: "等待生成"
        if (posts.isEmpty()) {
            recyclerView.visibility = View.GONE
            emptyView.visibility = View.VISIBLE
            return
        }
        recyclerView.visibility = View.VISIBLE
        emptyView.visibility = View.GONE
        recyclerView.adapter = PostListAdapter(this, posts) { post ->
            val intent = Intent(this, PostDetailActivity::class.java).apply {
                putExtra(PostDetailActivity.EXTRA_POST_ID, post.id)
            }
            startActivity(intent)
        }
    }

    /** 给根布局的顶部标题区域添加 status bar 高度 padding，避免与状态栏重叠。 */
    private fun applyStatusBarInsets() {
        val header = findViewById<View>(R.id.header)
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
}
