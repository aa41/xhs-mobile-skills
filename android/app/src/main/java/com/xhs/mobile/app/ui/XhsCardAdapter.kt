package com.xhs.mobile.app.ui

import android.content.Context
import android.view.LayoutInflater
import android.view.View
import android.view.ViewGroup
import android.widget.ImageView
import android.widget.TextView
import androidx.recyclerview.widget.RecyclerView
import com.xhs.mobile.app.R
import com.xhs.mobile.app.data.Card
import com.xhs.mobile.app.data.PostManifest
import com.xhs.mobile.app.util.Assets

/** 小红书卡片轮播（ViewPager2 内部用 RecyclerView.Adapter）。 */

class XhsCardAdapter(
    private val context: Context,
    private val post: PostManifest,
    private val cards: List<Card>
) : RecyclerView.Adapter<XhsCardAdapter.VH>() {

    class VH(view: View) : RecyclerView.ViewHolder(view) {
        val image: ImageView = view.findViewById(R.id.cardImage)
        val title: TextView = view.findViewById(R.id.cardTitle)
    }

    override fun onCreateViewHolder(parent: ViewGroup, viewType: Int): VH {
        val view = LayoutInflater.from(parent.context).inflate(R.layout.item_xhs_card, parent, false)
        return VH(view)
    }

    override fun onBindViewHolder(holder: VH, position: Int) {
        val card = cards[position]
        val bmp = Assets.decodeBitmap(context, post.cardAssetPath(card))
        if (bmp != null) holder.image.setImageBitmap(bmp) else holder.image.setImageResource(R.drawable.ic_placeholder)
        holder.title.text = card.title
    }

    override fun getItemCount(): Int = cards.size
}
