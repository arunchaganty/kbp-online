/*!
 * KBPOnline
 * Author: Arun Chaganty, Ashwin Paranjape
 * Licensed under the MIT license
 */

define(['jquery'], function($) {
  return {
    getDOMFromTemplate: function(url, cb) {
        $.ajax({
          url: url,
          success: function(html) {
            var elem = $(html);
            cb(elem);
          }});}
  };
});

