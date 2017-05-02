/*!
 * KBPOnline
 * Author: Arun Chaganty, Ashwin Paranjape
 * Licensed under the MIT license
 */

define(['jquery', '../util'], function ($, util) {
  var RemoveSpanWidget = function(elem, cb) {
    var self = this;
    this.elem = elem;

    util.getDOMFromTemplate('/static/kbpo/html/RemoveSpanWidget.html', function(elem_) {
      self.elem.find("#remove-span").on("click.kbpo.RemoveSpanWidget", function(evt) {
        self.clickListeners.forEach(function (cb) {cb(true);});
      });

      cb();
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
