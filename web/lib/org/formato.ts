export function mascararCnpj(cnpj: string): string {
  const digitos = cnpj.replace(/\D/g, "");
  if (digitos.length !== 14) return cnpj;
  return `${digitos.slice(0, 2)}.${digitos.slice(2, 5)}.${digitos.slice(5, 8)}/${digitos.slice(8, 12)}-${digitos.slice(12)}`;
}

export function dataHora(valor: string | null): string {
  if (!valor) return "—";
  const data = new Date(valor);
  return Number.isNaN(data.getTime())
    ? valor
    : data.toLocaleString("pt-BR", { day: "2-digit", month: "2-digit", year: "numeric", hour: "2-digit", minute: "2-digit" });
}

export function dia(valor: string): string {
  const data = new Date(`${valor.slice(0, 10)}T00:00:00Z`);
  return Number.isNaN(data.getTime()) ? valor : data.toLocaleDateString("pt-BR", { timeZone: "UTC", day: "2-digit", month: "2-digit" });
}

const reais = new Intl.NumberFormat("pt-BR", { style: "currency", currency: "BRL" });

export function brl(valor: string | number): string {
  const numero = typeof valor === "number" ? valor : Number(valor);
  return Number.isFinite(numero) ? reais.format(numero) : String(valor);
}

export function inteiro(valor: number): string {
  return valor.toLocaleString("pt-BR");
}
