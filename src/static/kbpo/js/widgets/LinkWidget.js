/*!
 * KBPOnline
 * Author: Arun Chaganty, Ashwin Paranjape
 * Licensed under the MIT license
 */

define(['jquery', 'bootstrap'], function($) {
    function LinkWidget(elem) {
        var self = this;

        this.elem = elem;

        this.resultLimit = 5;
        this.thumbSize = 50;

        $('#submit-wiki-search').click(function(){self.populate(this.form.search_input.value);});
        $('#no-wiki-link').click(function(){
            self.doneListeners.forEach(function(cb) {cb("");});
                self.hide();
        });
    }
    LinkWidget.prototype.doneListeners = [];

    LinkWidget.prototype.fetchResults = function(term) {
        return $.ajax({
            url: 'https://en.wikipedia.org/w/api.php',
            data: { action: 'opensearch', limit: this.resultLimit, search: term, format: 'json' , redirects:'resolve', namespace:0},
            dataType: 'jsonp',
        });
    };
    LinkWidget.prototype.fetchThumbs = function(searchResults) {
        return $.ajax({
            url: 'https://en.wikipedia.org/w/api.php',
            data: {action: 'query', titles: searchResults[1].join('|'), format: 'json', prop: 'pageimages', pithumbsize: this.thumbSize, pilimit:this.resultLimit},
            dataType: 'jsonp',
        });
    };

    LinkWidget.prototype.preload = function(mentionText) {
        this.mentionText = mentionText;
        this.populate(mentionText);
        $('#wiki-search-input').val(mentionText);
    };
    LinkWidget.prototype.show = function(mentionText) {
        if(this.mentionText != mentionText){
            this.mentionText = mentionText;
            this.populate(mentionText);
            $('#wiki-search-input').val(mentionText);
        }
        $('#wiki-linking-modal').modal('show');
    };

    LinkWidget.prototype.hide = function() {
        $('#wiki-linking-modal').modal('hide');
        $('.wiki-entry').not('.wiki-entry-template').not('.none-wiki-entry').remove();
    };

    LinkWidget.prototype.populate = function(mentionText) {
        if (mentionText === undefined) {
            mentionText = this.mentionText;
        }
        var self = this;
        var triggerDoneListeners = function(evt) {
            var url = $(this).siblings('.list-group-item-heading').children('a').attr('href');
            var name = url.substr(url.lastIndexOf('/') + 1);
            self.hide();
            self.doneListeners.forEach(function(cb) {cb(name);});
        };

        this.fetchResults(mentionText).done(function(searchResults) {
            if (searchResults[1].length === 0){
                //No results were found, simply clear and move on
                $('.wiki-entry').not('.wiki-entry-template').not('.none-wiki-entry').remove();
            }
            self.fetchThumbs(searchResults).done(function(images){
                var thumbs = [];
                if (images.query !== undefined) { // Try to get images.
                    var pages = images.query.pages;
                    for (var page in pages) {
                        if ('thumbnail' in pages[page]) {
                            thumbs.push(pages[page].thumbnail.source);
                        } else {
                            thumbs.push(null);
                        }
                    }
                } 
                searchResults.push(thumbs);

                var titles = searchResults[1];
                var texts = searchResults[2];
                var urls = searchResults[3];


                // Clear existing entries.
                $('.wiki-entry').not('.wiki-entry-template').not('.none-wiki-entry').remove();
                for(var i=titles.length-1; i>=0; i--) {
                    var resultDom = $('.wiki-entry-template').clone();
                    resultDom.removeClass('hidden').removeClass('wiki-entry-template');

                    resultDom.children('button').click(triggerDoneListeners);

                    resultDom.children('.list-group-item-heading').prepend('<a href=\"'+urls[i]+'\" target=\'_blank\'>'+titles[i]+'</a>');
                    if (thumbs[i] !== null) {
                        resultDom.prepend("<img src=\'"+thumbs[i]+"\' style='float:left; padding-right:3px;' class='img-responsive' ></img>");
                    }
                    resultDom.children('.list-group-item-text').append(texts[i]);
                    resultDom.prependTo($('#wiki-search-results'));
                }   
            });
        });
    };

    return LinkWidget;
});
