import type { Pagina } from "./tipos";

type RequisitarPagina<T> = (caminho: string) => Promise<Pagina<T>>;

export async function carregarTodosOsResultados<T>(
  caminho: string,
  requisitar: RequisitarPagina<T>,
): Promise<T[]> {
  const caminhoBackend = `/api/v2/${caminho.replace(/\/$/, "")}/`;
  const primeira = await requisitar(caminho);
  const resultados = [...primeira.results];
  let proximo = primeira.next;

  while (proximo) {
    const url = new URL(proximo, `https://tiss.invalid${caminhoBackend}`);
    if (url.pathname !== caminhoBackend) throw new Error("Link de paginação fora da rota permitida.");

    const pagina = await requisitar(`${caminho}${url.search}`);
    resultados.push(...pagina.results);
    proximo = pagina.next;
  }

  return resultados;
}
