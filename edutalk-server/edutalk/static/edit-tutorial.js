/* global ajaxJson:false lessonList:false reorder:false */

/*
 * edit-tutorial.js for teacher only
 *
 */

$(() => {
  // temporary clear local storage
  // otherwise lectures will be in wrong order
  // console.clear();

  localStorage.clear();
  sortableInit();
});

function sortableInit() {
  // Using Sortable.js
  const options = {
    dataIDAttr: 'data-id',
    animation: 150,
    forceFallback: true,
    store: {
      /**
       * Get the order of elements. Called once during initialization.
       * @param   {Sortable}  sortable
       * @returns {Array}
       */
      get(sortable) {
        const order = localStorage.getItem(sortable.options.group.name);
        return order ? order.split('|') : [];
      },

      /**
       * Save the order of elements. Called onEnd (when the item is dropped).
       * @param {Sortable}  sortable
       */
      set(sortable) {
        const order = sortable.toArray();
        ajaxJson(
          reorder,
          'POST',
          { order },
          () => {
            localStorage.setItem(sortable.options.group.name, order.join('|'));
          },
        );
      },
    }, // end store
  }; // end options
  Sortable.create(lessonList, options);
}
