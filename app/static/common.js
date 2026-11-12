/* Utilidades comunes. Todo texto que viene del servidor se inserta con textContent (nunca innerHTML). */
(function () {
  var TZ = "America/Bogota";
  var ESTADOS = { pendiente: "Pendiente", confirmado: "Hurto confirmado", descartado: "Falsa alarma" };

  function el(tag, props) {
    var nodo = document.createElement(tag);
    var p = props || {};
    Object.keys(p).forEach(function (k) {
      var v = p[k];
      if (v === null || v === undefined || v === false) return;
      if (k === "class") nodo.className = v;
      else if (k === "texto") nodo.textContent = v;
      else if (k.indexOf("on") === 0) nodo.addEventListener(k.slice(2), v);
      else nodo.setAttribute(k, v === true ? "" : v);
    });
    Array.prototype.slice.call(arguments, 2).forEach(function agregar(h) {
      if (h === null || h === undefined || h === false) return;
      if (Array.isArray(h)) return h.forEach(agregar);
      nodo.append(h.nodeType ? h : document.createTextNode(String(h)));
    });
    return nodo;
  }

  function fecha(iso) {
    if (!iso) return "—";
    return new Date(iso).toLocaleString("es-CO", { timeZone: TZ, dateStyle: "short", timeStyle: "medium" });
  }

  function api(url, opciones) {
    var cfg = Object.assign({ credentials: "same-origin", headers: { "Content-Type": "application/json" } }, opciones || {});
    return fetch(url, cfg).then(function (resp) {
      if (resp.status === 401) {
        window.location.href = "/login";
        throw new Error("Sesión vencida");
      }
      return resp.json().catch(function () { return null; }).then(function (cuerpo) {
        if (!resp.ok) {
          var detalle = cuerpo && cuerpo.detail;
          if (Array.isArray(detalle)) detalle = detalle.map(function (d) { return d.msg; }).join("; ");
          throw new Error(detalle || "Error " + resp.status);
        }
        return cuerpo;
      });
    });
  }

  function insignia(estado) {
    return el("span", { class: "insignia " + estado, texto: ESTADOS[estado] || estado });
  }

  function insigniaLatencia(ev) {
    if (ev.latencia_seg === null || ev.latencia_seg === undefined) return el("span", { class: "meta", texto: "—" });
    return el("span", { class: "insignia " + (ev.cumple_sla ? "ok" : "mal"), texto: ev.latencia_seg.toFixed(1) + " s" });
  }

  function mensaje(contenedor, texto, clase) {
    contenedor.replaceChildren(texto ? el("div", { class: "mensaje " + (clase || "error"), role: "alert", texto: texto }) : "");
  }

  window.App = { el: el, fecha: fecha, api: api, insignia: insignia, insigniaLatencia: insigniaLatencia, mensaje: mensaje, ESTADOS: ESTADOS };
})();
