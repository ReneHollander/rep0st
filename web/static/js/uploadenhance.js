var uploadPrompt = document.getElementById("image");
uploadPrompt.addEventListener('change', function (e) {
    var filename = e.target.value.split('\\').pop();
    document.getElementById("imageUpload").innerHTML = filename;
});