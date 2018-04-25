// Init Popover
$(function () {
  // Attaches a toggle popovers
  // Note: please use .popover-toggle class for the [data-toggle="popover"] 
  // element
  $('.popover-toggle').popover({
    container: 'body'
  });
  // Attaches a dismiss popovers
  // Note: please use .popover-dismiss class for the [data-toggle="popover"] 
  // element
  $('.popover-dismiss').popover({
    trigger: 'focus',
    container: 'body'
  });
});

// Init Tooltip
$(function () {
  // Attaches a tooltip for all of [data-toggle="tooltip"] elements
  $('[data-toggle="tooltip"]').tooltip();
});
function showTooltipWhenFocus(selector, message) {
  $(selector).tooltip('hide')
    .attr('data-original-title', message)
    .tooltip('show');  
  $(selector).attr('data-toggle', 'tooltip').tooltip();
  $(selector).on('mouseleave blur', function(){
    $(this).tooltip('hide');
  });
}
// some functions for tooltips
// function setTooltip(selector, message) {
//   $(selector).tooltip('hide')
//     .attr('data-original-title', message)
//     .tooltip('show');
// }
// function hideTooltip(selector) {
//   setTimeout(function() {
//     $(selector).tooltip('hide');
//   }, 1000);
// }

// Init Clipboard
// fallback message for clipboard failed
function clipboardFallbackMessage(action) {
    var actionMsg = '';
    var actionKey = (action === 'cut' ? 'X' : 'C');
    if (/iPhone|iPad/i.test(navigator.userAgent)) {
        actionMsg = 'No support :(';
    } else if (/Mac/i.test(navigator.userAgent)) {
        actionMsg = 'Press ⌘-' + actionKey + ' to ' + action;
    } else {
        actionMsg = 'Press Ctrl-' + actionKey + ' to ' + action;
    }
    return actionMsg;
}
$(function () {
  // Enable Normal Clipboard
  // Note: please use .btn-clipboard class for the [data-clipboard-target="#id"]
  // element
  var clipboard = new ClipboardJS('.btn-clipboard');
  // Event callback is optional. But if you want capture clipboard events, 
  // please implement those callbacks. Maybe after copied, you want show 
  // a feedback tooltips or clear the selected style.
  clipboard.on('success', function(e) {
      // console.info('Action:', e.action);
      // console.info('Text:', e.text);
      // console.info('Trigger:', e.trigger);

      // clear the selected style(maybe it's a blue background color)
      e.clearSelection();
      showTooltipWhenFocus(e.trigger, 'Copied!');
  });

  clipboard.on('error', function(e) {
      // console.error('Action:', e.action);
      // console.error('Trigger:', e.trigger);

      // fail to copy, do some fallback jobs
      showTooltipWhenFocus(e.trigger, clipboardFallbackMessage(e.action));
  });

  // Enable Code Snippets Clipboard
  // set next sibling element as copied target element
  // var snippetClipboard = new ClipboardJS('[data-clipboard-snippet]', {
  //   target: function(trigger) {
  //       return trigger.nextElementSibling;
  //   }
  // });

  // snippetClipboard.on('success', function(){
  //   e.clearSelection();

  // });

  // snippetClipboard.on('error', function(){

  // });
});