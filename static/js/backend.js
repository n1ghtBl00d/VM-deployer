window.timer = 0;

const socket = io()
var vmTable;
var templateList;

document.addEventListener('DOMContentLoaded', function(){

    console.log("Loaded Socket")
    document.getElementById('delAll').addEventListener("click", delAll);
    document.getElementById('updateVmList').addEventListener("click", updateStatus);
    document.getElementById('cloneTemplate').addEventListener("click", cloneTemplate);
    vmTable = document.getElementById('vmTable');
    templateList = document.getElementById('templatesDDL');
    socket.emit("getTemplates", "get");
    updateStatus()
    
});

function cloneTemplate(){
    console.log("entered cloneTemplate");
    var selectedValue = $("#templatesDDL").val();
    console.log(selectedValue);
    if(selectedValue == "NULL"){
        $("#ddlWarning").text("Please select a Template from the list");
    }else{
        socket.emit("cloneTemplate", selectedValue);
        $("#ddlWarning").text("");
    }
}

function delAll(){
    console.log("entered delAll");
    if(confirm("Are your sure you want to delete all currently running VMs?")){
        console.log("confirmed. Deleteing all");
        socket.emit("delAll", "start");
    }else{
        console.log("Cancelled");
    }
}

function updateStatus(){
    console.log("updateStatus");
    vmTable.innerHTML = "<tr><th style='width: 10%;'>ID</th><th style='width: 20%;'>Name</th><th style='width: 10%;'>Status</th><th style='width: 20%;'>IP Address</th><th style='width: 10%;'></th><th style='width: 10%;'></th><th style='width: 10%;'></th><th style='width: 10%;'></th></tr>";
    socket.emit("updateAllStatus", "start");
}

socket.on("statusUpdate", (data) => {
    console.log("statusUpdate");
    console.log(data.status);
    document.getElementById('output').innerHTML = "<p>ID: " + data.newID + " - " + data.status + "</p>";

});

socket.on("vmListEntry", (data) => {
    vncButton = ""
    if(data.vncStatus == true && data.status != "stopped"){
        vncButton = "<a href='/vnc?vmid=" + data.vmid +"' target='_blank'><button>VNC</button></a>"
    }
    var entryData = "<td>" + data.vmid + "</td><td>" + data.name + "</td><td>" + 
    data.status + "</td><td>" + data.ip + "</td><td><button class='delVM' data-vmid='" + data.vmid +"'>Delete</button></td>" +
    "</td><td><button class='rebootVM' data-vmid='" + data.vmid +"'>Reboot</button></td>" +
    "</td><td><button class='revertVM' data-vmid='" + data.vmid +"'>Reboot</button></td><td>" + vncButton + "</td>"

    var foundMatch = 0;
    currentEntries = document.querySelectorAll('[id^="VM"]')
    currentEntries.forEach(entry => {
        if(entry.id.includes(data.vmid)){
            entry.innerHTML = entryData;
            foundMatch = 1;
        }
    });
    if(foundMatch == 0){
        vmTable.innerHTML += "<tr id='VM" + data.vmid + "'>" + entryData + "</tr>"
    }
});

socket.on("TemplateList", (data) => {
    console.log("TemplateList");
    console.log(data);
    data.forEach(element => {
        templateList.innerHTML += "<option value='" + element.vmid +"'>" + element.name + "</option>"
    });
});

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
