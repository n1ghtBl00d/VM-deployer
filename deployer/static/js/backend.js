window.timer = 0;

const socket = io()
var vmTable;
var templateList;

document.addEventListener('DOMContentLoaded', function(){

    console.log("Loaded Socket")
    document.getElementById('delAll').addEventListener("click", delAll);
    document.getElementById('updateVmList').addEventListener("click", updateStatus);
    document.getElementById('cloneTemplate').addEventListener("click", cloneTemplate);
    document.getElementById('deployGroup').addEventListener("click", deployGroup);
    document.getElementById('firewallBtn').addEventListener("click", addFirewallRule);
    vmTable = document.getElementById('vmTable');
    console.log('SENDING MEESAGE')
    socket.emit("getTemplates", "get");
    socket.emit("getGroups", "get");
    updateStatus()
    
});

function sendAnnouncement() {
    let message = document.getElementById('message').value
    socket.emit("announcementMessage", message)
}

function cloneTemplate(){
    console.log("entered cloneTemplate");
    var selectedValue = $("#templatesDDL").val();
    console.log(selectedValue);
    if(selectedValue == "NULL"){
        $("#ddlWarning").text("Please select a Template from the list");
    }else{
        var numberOfClones = 1;
        if($('#multiClone').is(':checked')){
            numberOfClones = $('#numClones').val()
        }
        for (let i = 0; i < numberOfClones; i++) {
            setTimeout( () => {
                console.log("Cloned #" + (i+1) + " of " + numberOfClones)
                socket.emit("cloneTemplate", selectedValue);
            }, (i * 5000)); // ~5 second delay between each iteration
        }
        $("#ddlWarning").text("");
    }
}

function deployGroup(){
    console.log("entered deployGroup()")
    var selectedValue = $("#groupTemplatesDDL").val()
    if(selectedValue == "NULL"){
        $("#ddlWarning").text("Please select a Template from the list");
    }else{
        console.log("Copying group " + selectedValue)
        socket.emit("cloneGroup", selectedValue)
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
    vmTable.innerHTML = "<tr><th style='width: 10%;'>ID</th><th style='width: 20%;'>Name</th><th style='width: 10%;'>Status</th><th style='width: 20%;'>IP Address</th><th style='width: 10%;'></th><th style='width: 10%;'></th><th style='width: 10%;'></th><th style='width: 10%;'>Username</th></tr>";
    if (document.getElementById('forceUpdate').checked) {
        socket.emit("ForceUpdateAllStatus", "start");
    } else {
        socket.emit("updateAllStatus", "start");
    }
}

function addFirewallRule(){
    vmid = $("#firewallId").val()
    ipAddr = $("#firewallIP").val()
    if (/^(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$/.test(ipAddr)) {  
        socket.emit("addFirewallEntry", {"vmid": vmid, "ipAddr": ipAddr})
    } else{
        alert("You have entered an invalid IP address!") 
    } 
      
}

socket.on("statusUpdate", (data) => {
    console.log("statusUpdate");
    console.log(data.status);
    date = new Date();
    document.getElementById('output').innerHTML = "<p><span style='color:#00f;'>"+ date.toLocaleTimeString('en', {timeZone: 'America/Denver'}).split(' ')[0] + "></span> ID: " + data.newID + " - " + data.status + "</p>" + document.getElementById('output').innerHTML;

});

socket.on("statusUpdateGroup", (data) => {
    console.log("statusUpdate");
    console.log(data.status);
    date = new Date();
    document.getElementById('output').innerHTML = "<p><span style='color:#00f;'>"+ date.toLocaleTimeString('en', {timeZone: 'America/Denver'}).split(' ')[0] + "></span> Group: " + data.groupID + " - " + data.status + "</p>" + document.getElementById('output').innerHTML;

});

socket.on("vmListEntry", (data) => {
    vncButton = ""
    if(data.vncStatus == true && data.status != "stopped"){
        vncButton = "<a href='/vnc?vmid=" + data.vmid +"' target='_blank'><button>VNC</button></a>"
    }
    var entryData = "<td>" + data.vmid + "</td><td>" + data.name + "</td><td>" + 
    data.status + "</td><td>" + data.ip + "</td><td><button class='delVM' data-vmid='" + data.vmid +"'>Delete</button></td>" +
    "</td><td><button class='rebootVM' data-vmid='" + data.vmid +"'>Reboot</button></td>" +
    "</td><td><button class='revertVM' data-vmid='" + data.vmid +"'>Revert</button></td><td>" + data.username + "</td>" //vncButton used to be where data.username is

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
        $("#templatesDDL")[0].innerHTML += "<option value='" + element.vmid +"'>" + element.name + "</option>";
    });
});

socket.on("groupList", (data) => {
    console.log("groupList");
    console.log(data);
    data.forEach(element => {
        $("#groupTemplatesDDL")[0].innerHTML += "<option value='" + element.groupID +"'>" + element.groupName + "</option>";
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

