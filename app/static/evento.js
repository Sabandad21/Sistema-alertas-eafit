(function () {
  var el = App.el;
  var cont = document.getElementById("detalle");
  var id = cont.dataset.evento;
  var puedeDecidir = cont.dataset.decide === "si";

  function dato(etiqueta, valor) {
    return el("p", { class: "dato" }, el("span", { class: "meta", texto: etiqueta + ": " }), valor);
  }

  function pintar(ev, equipos) {
    var msg = el("div", { id: "mensaje" });
    var selEquipo = el("select", { id: "equipo" },
      el("option", { value: "", texto: "No identificado" }),
      equipos.map(function (e) { return el("option", { value: e.id, texto: e.numero_serie }); })
    );

    function decidir(accion) {
      var cuerpo = accion === "confirmar" ? JSON.stringify({ equipo_id: selEquipo.value ? Number(selEquipo.value) : null }) : undefined;
      App.api("/api/eventos/" + id + "/" + accion, { method: "POST", body: cuerpo })
        .then(function () { window.location.reload(); })
        .catch(function (e) { App.mensaje(msg, e.message); });
    }

    var acciones = null;
    if (puedeDecidir && ev.estado === "pendiente") {
      acciones = el("div", { class: "tarjeta" },
        el("h2", { class: "titulo-seccion", texto: "¿Qué decide?" }),
        el("p", { class: "meta", texto: "Si confirma el hurto, el sistema crea el ticket de incidente y marca el equipo como pendiente de reposición." }),
        el("div", { class: "filtros" },
          el("div", {}, el("label", { for: "equipo", texto: "Equipo afectado (opcional)" }), selEquipo),
          el("button", { type: "button", class: "peligro", onclick: function () { decidir("confirmar"); }, texto: "Confirmar hurto" }),
          el("button", { type: "button", class: "secundario", onclick: function () { decidir("descartar"); }, texto: "Descartar (falsa alarma)" })
        ),
        msg
      );
    }

    cont.replaceChildren(
      el("div", { class: "fila" },
        el("div", { class: "crece" },
          el("h1", { texto: ev.tipo_texto }),
          el("p", { class: "sub" }, App.insignia(ev.estado), " ", ev.sala.nombre + " · " + ev.sala.bloque),
          el("div", { class: "tarjeta" },
            dato("Fecha y hora", App.fecha(ev.ocurrido_en)),
            dato("Confianza del detector", Math.round(ev.confianza * 100) + " %"),
            dato("Tiempo hasta el aviso", App.insigniaLatencia(ev)),
            dato("Aviso por Teams", ev.notificado_teams ? "Enviado" : "No enviado"),
            dato("Equipo", ev.equipo || "—"),
            dato("Ticket", ev.ticket || "—")
          ),
          acciones
        ),
        ev.captura_url
          ? el("div", { class: "crece" }, el("img", { class: "grande", src: ev.captura_url, alt: "Captura de la cámara" }))
          : el("div", { class: "crece meta", texto: "Sin captura disponible para su rol o para este evento." })
      )
    );
  }

  App.api("/api/eventos/" + id)
    .then(function (ev) {
      var pedirEquipos = puedeDecidir && ev.estado === "pendiente"
        ? App.api("/api/equipos").then(function (todos) { return todos.filter(function (e) { return e.sala_id === ev.sala.id; }); })
        : Promise.resolve([]);
      return pedirEquipos.then(function (equipos) { pintar(ev, equipos); });
    })
    .catch(function (e) { App.mensaje(cont, e.message); });
})();
