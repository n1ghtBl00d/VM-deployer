window.timer = 0;

const socket = io()
var vmList;

document.addEventListener('DOMContentLoaded', function(){

    console.log("Loaded Socket")
    // document.getElementById('ResetRobotLib').addEventListener('click', resetRobotLib)
    document.getElementById('newVM').addEventListener("click", newVM);
    document.getElementById('newLXC').addEventListener("click", newLXC);
    document.getElementById('delAll').addEventListener("click", delAll);
    document.getElementById('updateVmList').addEventListener("click", updateStatus);
    vmList = document.getElementById('vmList');
    updateStatus()
});

function newVM(){
    console.log("entered newVM");
    socket.emit("newVM", "start");
}
function newLXC(){
    console.log("entered newLXC");
    socket.emit("newLXC", "start");
}

function delAll(){
    console.log("entered delAll");
    socket.emit("delAll", "start");
}

socket.on("statusUpdate", (data) => {
    console.log("statusUpdate");
    console.log(data.status);
    document.getElementById('output').innerHTML = "<p>ID: " + data.newID + " - " + data.status + "</p>";

});

socket.on("vmListEntry", (data) => {
    console.log("vmListEntry");
    vmList.innerHTML += "<li id='VM" + data.vmid + "'><span>ID: " + data.vmid +"</span> - <span>Name: " + 
        data.name + "</span> - <span>Status: " + data.status +"</span> - <span>IP: " + data.ip + 
        "</span> <button class='delVM' data-vmid='" + data.vmid +"'>Delete</button><button class='rebootVM' data-vmid='" + 
        data.vmid +"'>Reboot</button><button class='revertVM' data-vmid='" + data.vmid +"'>Revert</button>"
});

function updateStatus(){
    console.log("updateStatus");
    vmList.innerHTML = "";
    socket.emit("updateAllStatus", "start");
}

$(document).on("click", ".delVM", function(){
    var vmid = $(this).data('vmid')
    socket.emit("deleteVM", {"vmid": vmid})
    $('#VM'+vmid).remove()
});
$(document).on("click", ".rebootVM", function(){
    var vmid = $(this).data('vmid')
    socket.emit("reboot", {"vmid": vmid})
});
$(document).on("click", ".revertVM", function(){
    var vmid = $(this).data('vmid')
    socket.emit("revertState", {"vmid": vmid})
});
