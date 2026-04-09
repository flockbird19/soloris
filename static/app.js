async function upload() {
    let file = document.getElementById("fileInput").files[0];
    let formData = new FormData();
    formData.append("file", file);

    let res = await fetch("/verify", {
        method: "POST",
        body: formData
    });

    let data = await res.json();
    document.getElementById("result").innerText = data.deceased;
}

async function scan() {
    let res = await fetch("/scan");
    let data = await res.json();

    document.getElementById("output").innerText = data.data;
}