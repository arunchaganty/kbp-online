/*!
 * KBPOnline
 * Author: Arun Chaganty, Ashwin Paranjape
 * Licensed under the MIT license
 */

define(['jquery'], function ($) {
  /*
   * The entity link widget takes a mention and verifies its link (to Wikipedia)
   */
  function CheckWikiLinkWidget (elem) {
    this.elem = elem;
  }
  CheckWikiLinkWidget.prototype.init = function(mention){
    this.mention = mention;
    this.entity = this.mention.entity;
    // Skip if you have already verified your link
    if (this.entity.linkVerification !== undefined) {
      this.done();
      return;
    }
    // would this work?
    this.canonicalMention = this.entity.mentions[0];
    this.elem.find('#mention-gloss').text(this.mention.text());
    this.elem.find('#canonical-gloss').text(this.canonicalMention.text());

    var self = this;
    this.elem.find('#correct-wiki-link').on("click.kbpo.checkWikiLinkWidget", function(evt) {
      self.entity.linkCorrect = true;
      self.done();
    });
    this.elem.find('#wrong-wiki-link').on("click.kbpo.checkWikiLinkWidget", function(evt) {
      self.entity.linkCorrect = true;
      self.done();
    });

    this.elem.find('#mention-gloss').text(this.mention.text());
    //TODO: Make sure the wikilink is a valid wikipedia url

    //Do no ask for NIL clusters
    if(this.entity.link.substring(0, 3) == "NIL"){
      this.entity.linkCorrect = "NA";
      return;
    }
    if(this.mention.type.name == "TITLE" || this.mention.type.name == "DATE"){
      this.entity.linkCorrect = this.mention.type.name;
      return;
    }
    var searchStr;
    if (this.entity.link.substring(0,5) == "wiki:") { // Aha this is a wiki link!
      searchStr = this.entity.link.substring(5);
    } else {
      searchStr = this.entity.gloss;
    }

    $.ajax({
      url: 'https://en.wikipedia.org/w/api.php',
      data: { action: 'query', titles: searchStr, format: 'json',prop: 'extracts|pageimages' , exintro:"", pithumbsize: 150},
      dataType: 'jsonp'
    }).done(function(response) {
      var first = null;
      for(var ids in response.query.pages){
        if (ids == "-1" || ids == -1) break;
        first = response.query.pages[ids];
        break;
      }
      if (first !== null) {
        console.log(first.extract); 
        self.elem.find('#wiki-frame>div').html(first.extract);
        self.elem.find('#wiki-frame>h3>a').html(first.title);
        self.elem.find('#wiki-frame>h3>a').attr('href', "https://en.wikipedia.org/wiki/"+self.entity.link);
        if (first.thumbnail !== undefined) {
          self.elem.find('#wiki-frame>img').attr('src', first.thumbnail.source);
        }
      } else {
        self.mention.entity.linkCorrect = "invalid_link";
        //self.done();
        return;
      }
    });

  };
  CheckWikiLinkWidget.prototype.done = function(){
    this.elem.find('mention-gloss').text("");
    this.elem.find('canonical-gloss').text("");
    this.elem.find('#wiki-frame>div').empty();
    this.elem.find('#wiki-frame>h3>a').empty();
    this.elem.find('#wiki-frame>h3>a').attr('href', "");
    this.elem.find('#wiki-frame>img').attr('src', "");
    var self = this;
    if (!this.elem.hasClass('in')){
      if(self.cb !== undefined) {
        self.cb();
      }
      return;
    }else{
      this.elem.modal('hide');
      this.elem.on('hidden.bs.modal', function (e) {
        self.cb();
      });
    }

  };
  CheckWikiLinkWidget.prototype.show = function(){
    if (this.mention.entity.linkCorrect !== undefined){
      this.done();
      return;
    }else{
      this.elem.modal('show');
    }
  };

  return CheckWikiLinkWidget;
});
