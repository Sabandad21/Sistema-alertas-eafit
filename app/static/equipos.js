(function () {
  var el = App.el;
  var filas = document.getElementById("filas");

  App.api("/api/equipos").then(function (equipos) {
    filas.replaceChildren.apply(filas, equipos.map(function (e) {
      var pendiente = e.estado !== "activo";
      return el("tr", {},
        el("td", { texto: e.numero_serie }),
        el("td", { texto: e.sala }),
        el("td", {}, el("span", { class: "insignia " + (pendiente ? "pendiente" : "ok"), texto: pendiente ? "Pendiente de reposición" : "Activo" })),
        el("td", { texto: e.ticket || "—" }),
        el("td", {}, el("a", { href: "/aviso/" + encodeURIComponent(e.numero_serie), texto: "Ver aviso" }))
      );
    }));
  }).catch(function (e) { App.mensaje(document.getElementById("mensaje"), e.message); });
})();
