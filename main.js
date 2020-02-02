var shouldAdjustElements = true;

function toggleMissionTable(missionId, visible, e) {
  if (shouldAdjustElements) {
    missionTable = document.getElementById(missionId);
    missionTable.style.display = visible ? "block" : "none";
    missionTable.style.top = e.pageY + 10 + "px";
    missionTable.style.left = Math.max(0,
      Math.min(window.innerWidth - missionTable.clientWidth - 20,
        e.pageX + 10)) + "px";
  }
};

function toggleAdjustFlag() {
  shouldAdjustElements = !shouldAdjustElements;
  if (shouldAdjustElements) {
    for (let missionTable of document.getElementsByClassName("mission-data")) {
      missionTable.style.display = "none";
    }
  }
}

window.onload = function() {
  let cells = document.getElementsByClassName("cell-loc");
  for (let cell of cells) {
    cell.addEventListener("mouseover",
      toggleMissionTable.bind(this, cell.dataset["mission"], true));
    cell.addEventListener("mousemove",
      toggleMissionTable.bind(this, cell.dataset["mission"], true));
    cell.addEventListener("mouseout",
      toggleMissionTable.bind(this, cell.dataset["mission"], false));
    cell.addEventListener("click", toggleAdjustFlag.bind(this));
  };
};
