require=function n(e,t,i){function o(s,a){if(!t[s]){if(!e[s]){var l="function"==typeof require&&require;if(!a&&l)return l(s,!0);if(r)return r(s,!0);var c=new Error("Cannot find module '"+s+"'");throw c.code="MODULE_NOT_FOUND",c}var u=t[s]={exports:{}};e[s][0].call(u.exports,function(n){var t=e[s][1][n];return o(t||n)},u,u.exports,n,e,t,i)}return t[s].exports}for(var r="function"==typeof require&&require,s=0;s<i.length;s++)o(i[s]);return o}({"sphinx-rtd-theme":[function(n,e,t){var jQuery="undefined"!=typeof window?window.jQuery:n("jquery");e.exports.ThemeNav=function(){var n={navBar:null,win:null,winScroll:!1,winResize:!1,linkScroll:!1,winPosition:0,winHeight:null,docHeight:null,isRunning:!1};return n.enable=function(n){var e=this;e.isRunning||(e.isRunning=!0,jQuery(function(t){e.init(t),e.reset(),e.win.on("hashchange",e.reset),n&&e.win.on("scroll",function(){e.linkScroll||e.winScroll||(e.winScroll=!0,requestAnimationFrame(function(){e.onScroll()}))}),e.win.on("resize",function(){e.winResize||(e.winResize=!0,requestAnimationFrame(function(){e.onResize()}))}),e.onResize()}))},n.enableSticky=function(){this.enable(!0)},n.init=function(n){n(document);var e=this;this.navBar=n("div.wy-side-scroll:first"),this.win=n(window),n(document).on("click","[data-toggle='wy-nav-top']",function(){n("[data-toggle='wy-nav-shift']").toggleClass("shift"),n("[data-toggle='rst-versions']").toggleClass("shift")}).on("click",".wy-menu-vertical .current ul li a",function(){var t=n(this);n("[data-toggle='wy-nav-shift']").removeClass("shift"),n("[data-toggle='rst-versions']").toggleClass("shift"),e.toggleCurrent(t),e.hashChange()}).on("click","[data-toggle='rst-current-version']",function(){n("[data-toggle='rst-versions']").toggleClass("shift-up")}),n("table.docutils:not(.field-list,.footnote,.citation)").wrap("<div class='wy-table-responsive'></div>"),n("table.docutils.footnote").wrap("<div class='wy-table-responsive footnote'></div>"),n("table.docutils.citation").wrap("<div class='wy-table-responsive citation'></div>"),n(".wy-menu-vertical ul").not(".simple").siblings("a").each(function(){var t=n(this);expand=n('<span class="toctree-expand"></span>'),expand.on("click",function(n){return e.toggleCurrent(t),n.stopPropagation(),!1}),t.prepend(expand)})},n.reset=function(){var n=encodeURI(window.location.hash)||"#";try{var e=$(".wy-menu-vertical").find('[href="'+n+'"]');if(0===e.length){var t=$('.document a[href="'+n+'"]').closest("div.section");e=$(".wy-menu-vertical").find('[href="#'+t.attr("id")+'"]')}e.length>0&&($(".wy-menu-vertical .current").removeClass("current"),e.addClass("current"),e.closest("li.toctree-l1").addClass("current"),e.closest("li.toctree-l1").parent().addClass("current"),e.closest("li.toctree-l1").addClass("current"),e.closest("li.toctree-l2").addClass("current"),e.closest("li.toctree-l3").addClass("current"),e.closest("li.toctree-l4").addClass("current"))}catch(i){console.log("Error expanding nav for anchor",i)}},n.onScroll=function(){this.winScroll=!1;var n=this.win.scrollTop(),e=n+this.winHeight,t=this.navBar.scrollTop()+(n-this.winPosition);n<0||e>this.docHeight||(this.navBar.scrollTop(t),this.winPosition=n)},n.onResize=function(){this.winResize=!1,this.winHeight=this.win.height(),this.docHeight=$(document).height()},n.hashChange=function(){this.linkScroll=!0,this.win.one("hashchange",function(){this.linkScroll=!1})},n.toggleCurrent=function(n){var e=n.closest("li");e.siblings("li.current").removeClass("current"),e.siblings().find("li.current").removeClass("current"),e.find("> ul li.current").removeClass("current"),e.toggleClass("current")},n}(),"undefined"!=typeof window&&(window.SphinxRtdTheme={Navigation:e.exports.ThemeNav}),function(){for(var n=0,e=["ms","moz","webkit","o"],t=0;t<e.length&&!window.requestAnimationFrame;++t)window.requestAnimationFrame=window[e[t]+"RequestAnimationFrame"],window.cancelAnimationFrame=window[e[t]+"CancelAnimationFrame"]||window[e[t]+"CancelRequestAnimationFrame"];window.requestAnimationFrame||(window.requestAnimationFrame=function(e,t){var i=(new Date).getTime(),o=Math.max(0,16-(i-n)),r=window.setTimeout(function(){e(i+o)},o);return n=i+o,r}),window.cancelAnimationFrame||(window.cancelAnimationFrame=function(n){clearTimeout(n)})}()},{jquery:"jquery"}]},{},["sphinx-rtd-theme"]);