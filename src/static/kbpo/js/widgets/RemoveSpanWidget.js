/*!
 * KBPOnline
 * Author: Arun Chaganty, Ashwin Paranjape
 * Licensed under the MIT license
 */

define(['jquery'], function ($) {
    var RemoveSpanWidget = function(elem) {
      var self = this;
      this.elem = elem;
      this.elem.find("#remove-span").on("click.kbpo.RemoveSpanWidget", function(evt) {
        self.clickListeners.forEach(function (cb) {cb(true);});
      });
    };
    RemoveSpanWidget.prototype.clickListeners = [];
    RemoveSpanWidget.prototype.activate = function() {
      this.elem.removeClass("hidden");
    };
    RemoveSpanWidget.prototype.deactivate = function() {
      this.elem.addClass("hidden");
    };
    return RemoveSpanWidget;
});
