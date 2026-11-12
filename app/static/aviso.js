(function () {
  var el = App.el;
  var serie = document.getElementById("serie").dataset.serie;
  var destino = document.getElementById("resultado");

  fetch("/api/publico/equipos/" + encodeURIComponent(serie))
    .then(function (r) { return r.json().then(function (d) { return { ok: r.ok, datos: d }; }); })
    .then(function (r) {
      if (!r.ok) {
        destino.replaceChildren(el("div", { class: "mensaje error", texto: "No encontramos este equipo." }));
        return;
      }
      var d = r.datos;
      destino.className = "";
      destino.replaceChildren(
        el("div", { class: "aviso-grande " + (d.con_falla_reportada ? "falla" : "libre") },
          el("strong", { texto: d.con_falla_reportada ? "Equipo con caso abierto" : "Sin casos abiertos" }),
          el("p", { texto: d.mensaje }),
          d.ticket ? el("p", { class: "meta", texto: "Caso: " + d.ticket }) : null
        )
      );
    })
    .catch(function () { destino.replaceChildren(el("div", { class: "mensaje error", texto: "No se pudo consultar el estado." })); });
})();
