/* admin_classrooms.js — init HLS players in admin list view (Django 3.0) */
(function () {
    'use strict';

    function initPlayers() {
        var videos = document.querySelectorAll('video[data-hlssrc]');
        if (!videos.length) return;

        /* load HLS.js once, then init all videos */
        if (typeof Hls !== 'undefined') {
            attachAll(videos);
            return;
        }
        var s = document.createElement('script');
        s.src = 'https://cdn.jsdelivr.net/npm/hls.js@1.5.13/dist/hls.min.js';
        s.onload = function () { attachAll(videos); };
        document.head.appendChild(s);
    }

    function attachAll(videos) {
        for (var i = 0; i < videos.length; i++) {
            (function (video) {
                var src = video.getAttribute('data-hlssrc');
                if (!src) return;
                if (typeof Hls !== 'undefined' && Hls.isSupported()) {
                    var hls = new Hls({
                        maxBufferLength       : 8,
                        maxMaxBufferLength    : 15,
                        startLevel            : 0,
                        autoStartLoad         : true,
                        manifestLoadingTimeOut: 8000,
                    });
                    hls.loadSource(src);
                    hls.attachMedia(video);
                    hls.on(Hls.Events.MANIFEST_PARSED, function () {
                        video.play().catch(function () {});
                    });
                } else if (video.canPlayType('application/vnd.apple.mpegurl')) {
                    video.src = src;
                    video.play().catch(function () {});
                }
            })(videos[i]);
        }
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initPlayers);
    } else {
        initPlayers();
    }
})();
