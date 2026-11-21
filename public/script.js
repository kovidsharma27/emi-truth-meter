// Compare page: show only the boxes that belong to the chosen offer type.
// Hidden boxes are also disabled so the browser does not ask for them.
document.querySelectorAll(".mode-select").forEach(function (select) {
  function update() {
    document
      .querySelectorAll('.mode-fields[data-side="' + select.dataset.side + '"]')
      .forEach(function (box) {
        var on = box.dataset.mode === select.value;
        box.disabled = !on;
        box.hidden = !on;
      });
  }
  select.addEventListener("change", update);
  update();
});
