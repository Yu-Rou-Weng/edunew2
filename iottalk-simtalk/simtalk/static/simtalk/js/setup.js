let vm = new Vue({
  el: '#app',
  delimiters: ['[[', ']]'],
  data: data,
  methods: {
    checkParameter(obj) {
      obj.error = [];
      if(obj.min > obj.max){
        obj.error.push('Error: min > max');
      }
      if(obj.distribution == 'GA'){
        if(obj.mean <=0) {
          obj.error.push('Error: Gamma Distribution\'s mean should be positive.');
        }
        if(obj.var <=0) {
          obj.error.push('Error: Gamma Distribution\'s variance should be positive.');
        }
      }
    },
    checkInputValidity(dfo) {
      let valid = true;

      dfo.value_distributions.forEach((vd)=>{
        if(vd.error && vd.error.length > 0){
          valid = false;
        }
      })

      if(dfo.time_distribution.error && dfo.time_distribution.error.length > 0){
        valid = false;
      }

      return valid;
    },
    saveHandler(obj, event) {
      if (!this.checkInputValidity(obj)){
        /* if input not valid, don't hide the modal */
        event.preventDefault()
      } else {
        /* Send Request to SimTalk Server */
        axios
        .put(window.location.href,
             JSON.stringify([obj]),
             {headers: {'X-CSRFToken': csrftoken}})
        .then(response => {
          this.$nextTick(() => {
            this.$bvModal.hide(event.componentId);
          });
        })
        .catch(error => {
          alert(error);
          console.log(error);
        })
      }
    },
  },
})
