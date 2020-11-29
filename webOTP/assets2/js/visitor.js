// var apigClientFactory = require('aws-api-gateway-client').default;
function submitform(){
	console.log("Hello world!")
	console.log("Hello world!!!!!!!!!!!!!!!!!!!!!!!!!")
	var apigClient = apigClientFactory.newClient();
	var OTP = document.getElementById("InputName").value;
	return apigClient.webcamPost({}, {
      messages: [{
        type: 'unstructured',
        unstructured: {
          OTP: OTP,
          faceid: getQueryVariable("faceid")
        }
      }]
    }, {});
}

function getQueryVariable(variable){
       let query = window.location.search.substring(1);
       let vars = query.split("&");
       console.log(query)
       for (let i=0;i<vars.length;i++) {
               let pair = vars[i].split("=");
               if(pair[0] == variable){return pair[1];}
       }
       return(false);
}


function sendmessage(){
	submitform().then((response) => {
		console.log("Hello world!")
		console.log(response);
		document.getElementById('messagewindow').innerHTML=response["data"]["message"];
    	// y.innerHTML=response;
	}).catch((error) => {
        console.log('an error occurred', error);
      });
}

document.getElementById('submitbtn').addEventListener('click', sendmessage);