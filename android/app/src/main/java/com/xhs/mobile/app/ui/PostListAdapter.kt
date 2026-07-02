package com.xhs.mobile.app.ui

import android.content.Context
import android.view.LayoutInflater
import android.view.View
import android.view.ViewGroup
import android.widget.ImageView
import android.widget.TextView
import androidx.recyclerview.widget.RecyclerView
import com.xhs.mobile.app.R
import com.xhs.mobile.app.data.PostManifest
import com.xhs.mobile.app.util.Assets

class PostListAdapter(
    private val context: Context,
    private val posts: List<PostManifest>,
    private val onClick: (PostManifest) -> Unit
) : RecyclerView.Adapter<PostListAdapter.VH>() {

    class VH(view: View) : RecyclerView.ViewHolder(view) {
        val thumb: ImageView = view.findViewById(R.id.thumb)
        val title: TextView = view.findViewById(R.id.title)
        val meta: TextView = view.findViewById(R.id.meta)
        val tagRole: TextView = view.findViewById(R.id.tagRole)
    }

    override fun onCreateViewHolder(parent: ViewGroup, viewType: Int): VH {
        val view = LayoutInflater.from(parent.context).inflate(R.layout.item_post, parent, false)
        return VH(view)
    }

    override fun onBindViewHolder(holder: VH, position: Int) {
        val post = posts[position]
        holder.title.text = post.title
        holder.meta.text = "${post.date}  ·  ${post.cardCount} 张图"
        holder.tagRole.text = post.roleLabel

        val firstCard = post.cards.firstOrNull()
        if (firstCard != null) {
            val bmp = Assets.decodeBitmap(context, post.cardAssetPath(firstCard))
            if (bmp != null) holder.thumb.setImageBitmap(bmp) else holder.thumb.setImageResource(R.drawable.ic_placeholder)
        } else {
            holder.thumb.setImageResource(R.drawable.ic_placeholder)
        }

        holder.itemView.setOnClickListener { onClick(post) }
    }

    override fun getItemCount(): Int = posts.size
}
