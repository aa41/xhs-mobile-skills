package com.xhs.mobile.app.data

import android.content.Context
import org.json.JSONObject

/** 扫描 assets/posts 下各子目录的 manifest.json，按日期倒序返回。无全局 index，避免脏数据。 */

object PostRepository {

    private const val POSTS_DIR = "posts"

    fun loadAll(context: Context): List<PostManifest> {
        val assets = context.assets
        val dirs = runCatching { assets.list(POSTS_DIR) }.getOrNull() ?: return emptyList()

        val posts = mutableListOf<PostManifest>()
        for (dir in dirs.sorted()) {
            val manifestPath = "$POSTS_DIR/$dir/manifest.json"
            val text = runCatching { assets.open(manifestPath).bufferedReader().use { it.readText() } }
                .getOrNull() ?: continue
            runCatching { posts.add(parse(text)) }.onFailure {
                // 单条解析失败不影响整体列表
            }
        }
        return posts.sortedByDescending { it.date }
    }

    fun findById(context: Context, id: String): PostManifest? =
        loadAll(context).firstOrNull { it.id == id }

    private fun parse(text: String): PostManifest {
        val json = JSONObject(text)
        val cards = mutableListOf<Card>()
        val cardsArr = json.optJSONArray("cards")
        if (cardsArr != null) {
            for (i in 0 until cardsArr.length()) {
                val c = cardsArr.getJSONObject(i)
                cards.add(Card(c.optString("file"), c.optInt("index", i + 1), c.optString("title")))
            }
        }
        val wechatJson = json.optJSONObject("wechat")
        val wechat = wechatJson?.let {
            Wechat(
                it.optString("title"),
                it.optString("digest"),
                it.optString("html_file").takeIf { s -> s.isNotBlank() && s != "null" }
            )
        }
        val tags = mutableListOf<String>()
        json.optJSONArray("tags")?.let { arr ->
            for (i in 0 until arr.length()) tags.add(arr.getString(i))
        }
        val platforms = mutableListOf<String>()
        json.optJSONArray("platforms")?.let { arr ->
            for (i in 0 until arr.length()) platforms.add(arr.getString(i))
        }
        return PostManifest(
            id = json.optString("id"),
            date = json.optString("date"),
            slug = json.optString("slug"),
            title = json.optString("title"),
            role = json.optString("role", "daily-dev-log"),
            platforms = if (platforms.isEmpty()) listOf("xhs", "wechat") else platforms,
            caption = json.optString("caption"),
            tags = tags,
            cards = cards,
            wechat = wechat,
            style = json.optString("style").takeIf { it.isNotBlank() && it != "null" },
            palette = json.optString("palette").takeIf { it.isNotBlank() && it != "null" },
            layout = json.optString("layout").takeIf { it.isNotBlank() && it != "null" },
            cardCount = json.optInt("cardCount", cards.size)
        )
    }
}
