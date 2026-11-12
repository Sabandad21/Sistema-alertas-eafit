(function () {
  var el = App.el;
  var filas = document.getElementById("filas");
  var msg = document.getElementById("mensaje");
  var selSala = document.getElementById("sala");

  function fila(ev) {
    return el("tr", {},
      el("td", { texto: App.fecha(ev.ocurrido_en) }),
      el("td", { texto: ev.sala.nombre }),
      el("td", { texto: ev.tipo_texto }),
      el("td", {}, App.insignia(ev.estado)),
      el("td", {}, App.insigniaLatencia(ev)),
      el("td", { texto: ev.ticket || "—" }),
      el("td", {}, el("a", { href: "/evento/" + ev.id, texto: "Ver" }))
    );
  }

  function cargar() {
    var p = new URLSearchParams();
    if (selSala.value) p.set("sala_id", selSala.value);
    ["desde", "hasta", "estado"].forEach(function (id) {
      var v = document.getElementById(id).value;
      if (v) p.set(id, v);
    });
    App.api("/api/eventos?" + p.toString())
      .then(function (eventos) {
        App.mensaje(msg, "");
        if (!eventos.length) {
          filas.replaceChildren(el("tr", {}, el("td", { colspan: 7, class: "vacio", texto: "No hay eventos con esos filtros." })));
          return;
        }
        filas.replaceChildren.apply(filas, eventos.map(fila));
      })
      .catch(function (e) { App.mensaje(msg, e.message); });
  }

  document.getElementById("filtros").addEventListener("submit", function (e) { e.preventDefault(); cargar(); });

  App.api("/api/salas").then(function (salas) {
    salas.forEach(function (s) { selSala.append(el("option", { value: s.id, texto: s.nombre })); });
  }).finally(cargar);
})();
