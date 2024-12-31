var app = new Vue({
  el: '#app',
  delimiters: ['[[',']]'],
  data: {
    users: [],
    projects: [],
    devices: []
  },
  mounted () {
    // init data
    this.userReload();
    this.projectReload();
    this.deviceReload();
  },
  methods: {
    // -- User --
    userReload() {
      axios.get('/api/v0/admin/user')
           .then(response => {this.users = response.data.data})
           .catch(error => {alert(error);});
    },
    changeUserPass(user) {
      let pass = prompt("Enter new password.");
      if (!pass) {
          alert("Password shold not be empty.")
          return;
      }

      axios.post('/api/v0/admin/user/pass', {'id': user.u_id, 'password': pass})
           .then(response => {
             if(response.data.id == user.u_id) {
              alert('Change successfully.');
             }
           })
           .catch(error => {alert('Change failed.');});
    },
    deleteUser(user) {
      let idx = this.users.findIndex(obj=>{return obj.u_id == user.u_id});

      axios.delete('/api/v0/admin/user',
                   {'data': {'id': user.u_id}})
           .then(response => {
             if(response.data.id == user.u_id) {
              this.users.splice(idx, 1);
             }
           })
           .catch(error => {alert('Delete failed.');});
    },
    switchUser(user) {
      if (login_user == user.u_id) {
        if (!confirm('You will remove your permissions, are you sure?')) {
          return
        }
      }

      axios.post('/api/v0/admin/user/switch', {'id': user.u_id, 'is_admin': !user.is_admin})
           .then(response => {
             if(response.data.id == user.u_id) {
              user.is_admin = !user.is_admin;
             }
           })
           .catch(error => {alert('Change failed.');});
    },
    // -- Project --
    projectReload() {
      axios.get('/api/v0/admin/project')
           .then(response => {this.projects = response.data.data})
           .catch(error => {alert(error);});
    },
    stopProject(project) {
      axios.post('/api/v0/admin/project/stop',
                 {'u_id': project.u_id, 'p_id': project.p_id})
           .then(response => {
             if(response.data.p_id == project.p_id) {
              project.status = 'off';
             }
           })
           .catch(error => {alert('Change failed.');});
    },
    stopSim(project) {
      alert("TODO");
    },
    deleteProject(project) {
      let idx = this.projects.findIndex(obj=>{return obj.p_id == project.p_id});

      axios.post('/api/v0/admin/project/delete',
                 {'u_id': project.u_id, 'p_id': project.p_id})
           .then(response => {
             if(response.data.p_id == project.p_id) {
              this.projects.splice(idx, 1);
             }
           })
           .catch(error => {alert('Delete failed.');});
    },
    // -- Device --
    deviceReload() {
      axios.get('/api/v0/admin/device')
           .then(response => {this.devices = response.data.data})
           .catch(error => {alert(error);});
    },
    unbindDevice(device) {
      axios.post('/api/v0/admin/device/unbind',
                 {'d_id': device.d_id})
           .then(response => {
             if(response.data.d_id == device.d_id) {
              alert('Unbind successfully.');
              this.deviceReload();
             }
           })
           .catch(error => {alert('Unbind failed.');});
    },
  }
})