package com.xhs.mobile.app.data

/** 对应 assets/posts/<id>/manifest.json 的数据模型。 */

data class Card(
    val file: String,        // 相对 post 目录，如 "images/01.png"
    val index: Int = 0,
    val title: String = ""
)

data class Wechat(
    val title: String = "",
    val digest: String = "",
    val html_file: String? = null
)

data class PostManifest(
    val id: String,
    val date: String,
    val slug: String = "",
    val title: String,
    val role: String = "daily-dev-log",
    val platforms: List<String> = listOf("xhs", "wechat"),
    val caption: String = "",
    val tags: List<String> = emptyList(),
    val cards: List<Card> = emptyList(),
    val wechat: Wechat? = null,
    val style: String? = null,
    val palette: String? = null,
    val layout: String? = null,
    val cardCount: Int = 0
) {
    /** 卡片图在 assets 中的完整路径：posts/<id>/images/01.png */
    fun cardAssetPath(card: Card): String = "posts/$id/${card.file}"

    /** 微信公众号 HTML 在 assets 中的完整路径（若存在）。 */
    fun wechatHtmlAssetPath(): String? = wechat?.html_file?.let { "posts/$id/$it" }

    val roleLabel: String
        get() = when (role) {
            "daily-dev-log" -> "每日开发日志"
            "weekly-dev-log" -> "每周开发日志"
            "release-note" -> "版本更新"
            "daily-ops" -> "日常运营"
            "product-diary" -> "产品日记"
            else -> role
        }
}
