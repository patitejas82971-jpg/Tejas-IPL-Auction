package com.iplauction.app

import android.annotation.SuppressLint
import android.app.DownloadManager
import android.content.Context
import android.content.Intent
import android.net.Uri
import android.os.Bundle
import android.os.Environment
import android.view.View
import android.webkit.CookieManager
import android.webkit.DownloadListener
import android.webkit.URLUtil
import android.webkit.WebChromeClient
import android.webkit.WebResourceError
import android.webkit.WebResourceRequest
import android.webkit.WebSettings
import android.webkit.WebView
import android.webkit.WebViewClient
import android.widget.Toast
import androidx.activity.OnBackPressedCallback
import androidx.appcompat.app.AppCompatActivity
import androidx.core.content.ContextCompat
import com.iplauction.app.databinding.ActivityMainBinding

class MainActivity : AppCompatActivity() {

    private lateinit var binding: ActivityMainBinding
    private var backPressedTime: Long = 0
    private var hasError: Boolean = false

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        binding = ActivityMainBinding.inflate(layoutInflater)
        setContentView(binding.root)

        initViews()
        setupWebView()
        setupBackNavigation()

        val initialUrl = ServerConfigDialog.getServerUrl(this)
        loadUrl(initialUrl)
    }

    private fun initViews() {
        // Toolbar settings button
        binding.btnSettings.setOnClickListener {
            ServerConfigDialog.show(this) { newUrl ->
                loadUrl(newUrl)
            }
        }

        // Swipe Refresh Layout
        binding.swipeRefreshLayout.setColorSchemeColors(
            ContextCompat.getColor(this, R.color.primary),
            ContextCompat.getColor(this, R.color.secondary)
        )
        binding.swipeRefreshLayout.setOnRefreshListener {
            binding.webView.reload()
        }

        // Keep swipe-to-refresh enabled only when scrolled to top
        binding.webView.viewTreeObserver.addOnScrollChangedListener {
            binding.swipeRefreshLayout.isEnabled = (binding.webView.scrollY == 0)
        }

        // Offline Error layout buttons
        binding.layoutOffline.btnRetry.setOnClickListener {
            hideOfflineError()
            val currentUrl = binding.webView.url ?: ServerConfigDialog.getServerUrl(this)
            loadUrl(currentUrl)
        }

        binding.layoutOffline.btnChangeServer.setOnClickListener {
            ServerConfigDialog.show(this) { newUrl ->
                hideOfflineError()
                loadUrl(newUrl)
            }
        }
    }

    @SuppressLint("SetJavaScriptEnabled")
    private fun setupWebView() {
        val settings = binding.webView.settings
        settings.javaScriptEnabled = true
        settings.domStorageEnabled = true
        settings.databaseEnabled = true
        settings.allowFileAccess = true
        settings.allowContentAccess = true
        settings.useWideViewPort = true
        settings.loadWithOverviewMode = true
        settings.mixedContentMode = WebSettings.MIXED_CONTENT_ALWAYS_ALLOW
        settings.mediaPlaybackRequiresUserGesture = false
        settings.cacheMode = WebSettings.LOAD_DEFAULT

        // Enable Cookies & Session persistence for Flask-Login
        val cookieManager = CookieManager.getInstance()
        cookieManager.setAcceptCookie(true)
        cookieManager.setAcceptThirdPartyCookies(binding.webView, true)

        // Native JavaScript bridge for bidding haptics, notifications, sharing
        binding.webView.addJavascriptInterface(WebAppInterface(this), "AndroidBridge")

        // Chrome client for progress updates
        binding.webView.webChromeClient = object : WebChromeClient() {
            override fun onProgressChanged(view: WebView?, newProgress: Int) {
                if (newProgress < 100) {
                    binding.progressBar.visibility = View.VISIBLE
                    binding.progressBar.progress = newProgress
                } else {
                    binding.progressBar.visibility = View.GONE
                }
            }
        }

        // Custom WebViewClient for internal navigation & error intercept
        binding.webView.webViewClient = object : WebViewClient() {
            override fun shouldOverrideUrlLoading(view: WebView?, request: WebResourceRequest?): Boolean {
                val url = request?.url?.toString() ?: return false

                // Handle standard HTTP/HTTPS links
                if (url.startsWith("http://") || url.startsWith("https://")) {
                    return false // Let WebView load it
                }

                // Handle external schemes (e.g. mailto:, tel:, whatsapp:)
                try {
                    val intent = Intent(Intent.ACTION_VIEW, Uri.parse(url))
                    startActivity(intent)
                    return true
                } catch (e: Exception) {
                    return false
                }
            }

            override fun onPageStarted(view: WebView?, url: String?, favicon: android.graphics.Bitmap?) {
                super.onPageStarted(view, url, favicon)
                hasError = false
            }

            override fun onPageFinished(view: WebView?, url: String?) {
                super.onPageFinished(view, url)
                binding.swipeRefreshLayout.isRefreshing = false
                CookieManager.getInstance().flush()

                if (!hasError) {
                    hideOfflineError()
                }
            }

            override fun onReceivedError(
                view: WebView?,
                request: WebResourceRequest?,
                error: WebResourceError?
            ) {
                super.onReceivedError(view, request, error)
                if (request?.isForMainFrame == true) {
                    hasError = true
                    showOfflineError(error?.description?.toString())
                }
            }
        }

        // File download listener for CSV and JSON squad results export
        binding.webView.setDownloadListener(DownloadListener { url, userAgent, contentDisposition, mimetype, _ ->
            try {
                val request = DownloadManager.Request(Uri.parse(url)).apply {
                    setMimeType(mimetype)
                    addRequestHeader("cookie", CookieManager.getInstance().getCookie(url))
                    addRequestHeader("User-Agent", userAgent)
                    setDescription(getString(R.string.download_started))
                    setTitle(URLUtil.guessFileName(url, contentDisposition, mimetype))
                    setNotificationVisibility(DownloadManager.Request.VISIBILITY_VISIBLE_NOTIFY_COMPLETED)
                    setDestinationInExternalPublicDir(
                        Environment.DIRECTORY_DOWNLOADS,
                        URLUtil.guessFileName(url, contentDisposition, mimetype)
                    )
                }

                val downloadManager = getSystemService(Context.DOWNLOAD_SERVICE) as? DownloadManager
                downloadManager?.enqueue(request)
                Toast.makeText(this, getString(R.string.download_started), Toast.LENGTH_SHORT).show()
            } catch (e: Exception) {
                // Fallback to opening in external browser
                val intent = Intent(Intent.ACTION_VIEW, Uri.parse(url))
                startActivity(intent)
            }
        })
    }

    private fun setupBackNavigation() {
        onBackPressedDispatcher.addCallback(this, object : OnBackPressedCallback(true) {
            override fun handleOnBackPressed() {
                if (binding.layoutOffline.offlineContainer.visibility == View.VISIBLE) {
                    if (binding.webView.canGoBack()) {
                        hideOfflineError()
                        binding.webView.goBack()
                        return
                    }
                }

                if (binding.webView.canGoBack()) {
                    binding.webView.goBack()
                } else {
                    if (System.currentTimeMillis() - backPressedTime < 2000) {
                        isEnabled = false
                        finish()
                    } else {
                        backPressedTime = System.currentTimeMillis()
                        Toast.makeText(this@MainActivity, getString(R.string.exit_prompt), Toast.LENGTH_SHORT).show()
                    }
                }
            }
        })
    }

    private fun loadUrl(url: String) {
        hideOfflineError()
        binding.swipeRefreshLayout.isRefreshing = true
        binding.webView.loadUrl(url)
    }

    private fun showOfflineError(details: String? = null) {
        binding.swipeRefreshLayout.isRefreshing = false
        binding.webView.visibility = View.GONE
        binding.layoutOffline.offlineContainer.visibility = View.VISIBLE
        if (!details.isNullOrEmpty()) {
            binding.layoutOffline.tvErrorDetails.text = "${getString(R.string.connection_error_desc)}\n($details)"
        }
    }

    private fun hideOfflineError() {
        binding.layoutOffline.offlineContainer.visibility = View.GONE
        binding.webView.visibility = View.VISIBLE
    }

    override fun onDestroy() {
        binding.webView.destroy()
        super.onDestroy()
    }
}
