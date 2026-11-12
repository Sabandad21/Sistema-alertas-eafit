(function () {
  var el = App.el;
  var lista = document.getElementById("lista");
  var estado = document.getElementById("estado-vivo");
  var tituloOriginal = document.title;
  var pendientes = 0;

  function tarjeta(ev, nueva) {
    var miniatura = ev.captura_url
      ? el("img", { class: "miniatura", src: ev.captura_url, alt: "Captura de la cámara en " + ev.sala.nombre })
      : null;
    return el("div", { class: "tarjeta" + (nueva ? " nueva" : ""), "data-id": ev.id },
      el("div", { class: "fila" },
        miniatura,
        el("div", { class: "crece" },
          el("strong", { texto: ev.tipo_texto }),
          el("div", { class: "meta", texto: ev.sala.nombre + " · " + ev.sala.bloque }),
          el("div", { class: "meta", texto: App.fecha(ev.ocurrido_en) + " · confianza " + Math.round(ev.confianza * 100) + " %" }),
          el("div", { class: "meta" }, "Tiempo hasta el aviso: ", App.insigniaLatencia(ev))
        ),
        el("a", { class: "boton", href: "/evento/" + ev.id, texto: "Revisar" })
      )
    );
  }

  function pintarVacio() {
    if (!lista.querySelector(".tarjeta")) {
      lista.replaceChildren(el("p", { class: "vacio", id: "vacio", texto: "No hay alertas pendientes." }));
    }
  }

  function agregar(ev, nueva) {
    var vacio = document.getElementById("vacio");
    if (vacio) vacio.remove();
    lista.prepend(tarjeta(ev, nueva));
  }

  App.api("/api/eventos?estado=pendiente&limite=50")
    .then(function (eventos) {
      eventos.slice().reverse().forEach(function (ev) { agregar(ev, false); });
      pendientes = eventos.length;
      pintarVacio();
    })
    .catch(function (e) { App.mensaje(lista, e.message); });

  var fuente = new EventSource("/api/alertas/stream");
  fuente.onopen = function () { estado.textContent = "En vivo"; estado.classList.add("conectado"); };
  fuente.onerror = function () { estado.textContent = "Reconectando…"; estado.classList.remove("conectado"); };
  fuente.onmessage = function (m) {
    var datos = JSON.parse(m.data);
    if (datos.tipo !== "alerta") return;
    agregar(datos.evento, true);
    pendientes += 1;
    document.title = "(" + pendientes + ") Nueva alerta · " + tituloOriginal;
  };
})();
