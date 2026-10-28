package com.iplauction.app

import android.content.Context
import android.view.LayoutInflater
import android.widget.Button
import android.widget.EditText
import com.google.android.material.dialog.MaterialAlertDialogBuilder

object ServerConfigDialog {

    private const val PREFS_NAME = "ipl_auction_prefs"
    private const val KEY_SERVER_URL = "server_url"
    const val DEFAULT_EMULATOR_URL = "http://10.0.2.2:5000"
    const val DEFAULT_LOCALHOST_URL = "http://127.0.0.1:5000"

    fun getServerUrl(context: Context): String {
        val prefs = context.getSharedPreferences(PREFS_NAME, Context.MODE_PRIVATE)
        return prefs.getString(KEY_SERVER_URL, DEFAULT_EMULATOR_URL) ?: DEFAULT_EMULATOR_URL
    }

    fun setServerUrl(context: Context, url: String) {
        val formatted = if (!url.startsWith("http://") && !url.startsWith("https://")) {
            "http://$url"
        } else {
            url
        }.trim().trimEnd('/')

        val prefs = context.getSharedPreferences(PREFS_NAME, Context.MODE_PRIVATE)
        prefs.edit().putString(KEY_SERVER_URL, formatted).apply()
    }

    fun show(context: Context, onUrlChanged: (String) -> Unit) {
        val inflater = LayoutInflater.from(context)
        val view = inflater.inflate(R.layout.dialog_server_config, null)
        val etUrl = view.findViewById<EditText>(R.id.etServerUrl)
        val btnEmulator = view.findViewById<Button>(R.id.btnPresetEmulator)
        val btnLocalhost = view.findViewById<Button>(R.id.btnPresetLocalhost)

        val currentUrl = getServerUrl(context)
        etUrl.setText(currentUrl)
        etUrl.setSelection(currentUrl.length)

        btnEmulator.setOnClickListener {
            etUrl.setText(DEFAULT_EMULATOR_URL)
            etUrl.setSelection(DEFAULT_EMULATOR_URL.length)
        }

        btnLocalhost.setOnClickListener {
            etUrl.setText(DEFAULT_LOCALHOST_URL)
            etUrl.setSelection(DEFAULT_LOCALHOST_URL.length)
        }

        MaterialAlertDialogBuilder(context)
            .setView(view)
            .setPositiveButton(context.getString(R.string.dialog_save)) { _, _ ->
                val newUrl = etUrl.text.toString().trim()
                if (newUrl.isNotEmpty()) {
                    setServerUrl(context, newUrl)
                    onUrlChanged(getServerUrl(context))
                }
            }
            .setNegativeButton(context.getString(R.string.dialog_cancel), null)
            .show()
    }
}
