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
  // the default trigger is 'hover focus'
  $('[data-toggle="tooltip"]').tooltip();
});
function showTooltipWhenFocus(selector, message, placement='top') {
  // remove element's title attribute
  var title = $(selector).attr('title');
  $(selector).attr('title', null);
  // add tooltip for element
  $(selector).tooltip({
    placement: placement,
    title: message
  });
  // show tooltip
  $(selector).tooltip('show');
  // destory tooltip and recover element's title
  $(selector).on('mouseleave blur', function(){
    $(this).tooltip('dispose');
    if (title !== undefined) {
      $(this).attr('title', title);
    }
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
// Message for clipboard
function clipboardMessage(action, success) {
    var actionMsg = '';
    if (success) {
      actionMsg = (action === 'cut' ? 'Cut!' : 'Copied!')
      return actionMsg;
    }
    // fallback message for clipboard failed
    var actionKey = (action === 'cut' ? 'X' : 'C');
    if (/iPhone|iPad/i.test(navigator.userAgent)) {
        actionMsg = 'Failed! No support :(';
    } else if (/Mac/i.test(navigator.userAgent)) {
        actionMsg = 'Failed! Press ⌘-' + actionKey + ' to ' + action;
    } else {
        actionMsg = 'Failed! Press Ctrl-' + actionKey + ' to ' + action;
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
      showTooltipWhenFocus(e.trigger, clipboardMessage(e.action, true));
  });

  clipboard.on('error', function(e) {
      // console.error('Action:', e.action);
      // console.error('Trigger:', e.trigger);

      // fail to copy, do some fallback jobs
      showTooltipWhenFocus(e.trigger, clipboardMessage(e.action, false));
  });

  // Enable Code Snippets Clipboard
  // Note: set next sibling element as copied target element
  var snippetClipboard = new ClipboardJS('[data-clipboard-snippet]', {
    target: function(trigger) {
        return trigger.nextElementSibling;
    }
  });

  snippetClipboard.on('success', function(e){
    e.clearSelection();
    showTooltipWhenFocus(e.trigger, clipboardMessage(e.action, true));
  });

  snippetClipboard.on('error', function(e){
    showTooltipWhenFocus(e.trigger, clipboardMessage(e.action, false));
  });
});