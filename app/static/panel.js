(function () {
  var el = App.el;
  var msg = document.getElementById("mensaje");

  function indicador(valor, etiqueta) {
    return el("div", { class: "indicador" }, el("div", { class: "valor", texto: valor }), el("div", { class: "etiqueta", texto: etiqueta }));
  }

  function barras(destino, filas, clave) {
    if (!filas.length) { destino.replaceChildren(el("p", { class: "vacio", texto: "Sin hurtos confirmados." })); return; }
    var maximo = Math.max.apply(null, filas.map(function (f) { return f.hurtos; }));
    destino.replaceChildren.apply(destino, filas.map(function (f) {
      var relleno = el("div", { class: "barra-valor" });
      relleno.style.width = Math.round(100 * f.hurtos / maximo) + "%"; // por CSSOM: permitido por la política de seguridad
      return el("div", { class: "barra-fila" },
        el("span", { texto: f[clave] }),
        el("div", { class: "barra-fondo" }, relleno),
        el("strong", { texto: f.hurtos })
      );
    }));
  }

  App.api("/api/reportes/cifras").then(function (c) {
    var usd = new Intl.NumberFormat("es-CO", { style: "currency", currency: "USD", maximumFractionDigits: 0 });
    var lat = c.latencia;
    document.getElementById("indicadores").replaceChildren(
      indicador(c.hurtos_confirmados, "Hurtos confirmados"),
      indicador(usd.format(c.costo_estimado_usd), "Costo estimado (" + usd.format(c.costo_por_equipo_usd) + " por equipo)"),
      indicador(c.porcentaje_falsas_alarmas === null ? "—" : c.porcentaje_falsas_alarmas + " %", "Falsas alarmas entre las revisadas"),
      indicador(c.pendientes, "Alertas pendientes de revisar"),
      indicador(lat.porcentaje_dentro_sla === null ? "—" : lat.porcentaje_dentro_sla + " %", "Avisos en menos de " + lat.sla_segundos + " s"),
      indicador(lat.promedio_seg === null ? "—" : lat.promedio_seg + " s", "Tiempo promedio hasta el aviso")
    );
    barras(document.getElementById("por-sala"), c.por_sala, "sala");
    barras(document.getElementById("por-mes"), c.por_mes, "mes");
  }).catch(function (e) { App.mensaje(msg, e.message); });
})();
