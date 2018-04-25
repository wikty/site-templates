// Init Popover
$(function () {
  // Enable toggle popovers
  // Note: please use .popover-toggle class for the element
  $('.popover-toggle').popover({
    container: 'body'
  });
  // Enable dismiss popovers
  // Note: please use .popover-dismiss class for the element
  $('.popover-dismiss').popover({
    trigger: 'focus',
    container: 'body'
  });
});

// Init Clipboard
$(function () {
  // Enable clipboard.js
  // Note: please use .btn-clipboard class for the element
  var clipboard = new ClipboardJS('.btn-clipboard');
  // optional, if you capture clipboard events, please fill the following callback
  clipboard.on('success', function(e) {
      // console.info('Action:', e.action);
      // console.info('Text:', e.text);
      // console.info('Trigger:', e.trigger);

      // e.clearSelection();
  });

  clipboard.on('error', function(e) {
      // console.error('Action:', e.action);
      // console.error('Trigger:', e.trigger);
  });
});