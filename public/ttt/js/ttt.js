(function () {
  var playerContainer = document.querySelector("#livePlayerContainer");
  async function init() {
    const response = await fetch(
      "https://icecast.smartdata.link/status-json.xsl"
    );
    const data = await response.json();
    console.log(data.icestats);
    if (data.icestats.source) {
      playerContainer.style.display = "block";
    } else {
      console.log("no live stream");
      playerContainer.style.display = "none";
    }
  }
  init();
})();
