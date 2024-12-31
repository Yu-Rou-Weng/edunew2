let vm = new Vue({
  el: '#app',
  delimiters: ['[[', ']]'],
  data: data,
  methods: {
    saveHandler: function(event){
      axios
      .put(window.location.href,
           JSON.stringify(this.$data.do_list),
           {headers: {'X-CSRFToken': csrftoken}})
      .then(response => {
        window.opener.postMessage('SimTalk start', "*");
        window.close();
      })
      .catch(error => {
        console.log(error);
      })
    },
  },
})
