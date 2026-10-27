import { NextResponse } from "next/server";
import type { RespostaDoBackend } from "./backend";
import { apagarPar, gravarPar } from "./credencial";

/** Devolve ao navegador o que o backend respondeu e grava o par renovado no caminho. */
export function respostaDoBackend(resultado: RespostaDoBackend): NextResponse {
  let resposta: NextResponse;
  if (resultado.fluxo) {
    resposta = new NextResponse(resultado.fluxo, {
      status: resultado.status,
      headers: { "content-type": "text/event-stream", "cache-control": "no-cache", "x-accel-buffering": "no" },
    });
  } else if (resultado.status === 204) {
    resposta = new NextResponse(null, { status: 204 });
  } else {
    resposta = NextResponse.json(resultado.corpo, { status: resultado.status });
  }
  if (resultado.par === null) apagarPar(resposta);
  else if (resultado.par) gravarPar(resposta, resultado.par);
  return resposta;
}
