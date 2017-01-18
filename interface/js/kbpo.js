/*
 * KBP online.
 * Arun Chaganty <arunchaganty@gmail.com>
 */

/**
 * The document object -- handles the storage and representation of
 * sentences.
 *
 * @elemId - DOM element that the document is rooted at.
 */
var DocWidget = function(elem) {
  console.assert(elem);
  this.elem = $(elem);
};

/**
 * Renders document stored in @doc.
 */
DocWidget.prototype.load = function(doc) {
  this.doc = doc;
  // Load every sentence into the DOM.
  for (var i = 0; i < doc.sentences.length; i++) {
    sentence = doc.sentences[i];
    var span = $("<span>", {'class': 'sentence', 'id': 'sentence-' + i});

    for (var j = 0; j < sentence.length; j++) {
      var token = sentence[j];
      var tokenSpan = $("<span>", {'class': 'token', 'id': 'token-' + i + '-' + j})
                   .text(token.word);
      if (j > 0 && sentence[j].doc_char_begin > sentence[j-1].doc_char_end) {
        tokenSpan.addClass("with-space");
      }
      span.append(tokenSpan);
    }
    this.elem.append(span);
  };
}
