import type { Referencias as ReferenciasType } from "../types";
import { formatNumeroCL, formatPct, formatUSD } from "../lib/format";
import Cifra from "./Cifra";
import "./Referencias.css";

export default function Referencias({ referencias }: { referencias: ReferenciasType }) {
  const { chile } = referencias;

  return (
    <div className="referencias">
      <ul className="referencias-indices">
        {referencias.indices.map((i) => (
          <li key={i.ticker}>
            <span className="referencias-ticker">{i.ticker}</span>
            <span>{formatUSD(i.precio)}</span>
            <span className={i.var_dia_pct >= 0 ? "var-positiva" : "var-negativa"}>
              {formatPct(i.var_dia_pct)}
            </span>
          </li>
        ))}
      </ul>
      <dl className="referencias-chile">
        <div>
          <dt>IPSA</dt>
          <dd>
            <Cifra valor={formatNumeroCL(chile.ipsa, 0)} fuente={chile.fuente} />
          </dd>
        </div>
        <div>
          <dt>UF</dt>
          <dd>
            <Cifra valor={`$${formatNumeroCL(chile.uf, 2)}`} fuente={chile.fuente} />
          </dd>
        </div>
        <div>
          <dt>Dólar</dt>
          <dd>
            <Cifra valor={`$${formatNumeroCL(chile.dolar, 2)}`} fuente={chile.fuente} />
          </dd>
        </div>
        <div>
          <dt>TPM</dt>
          <dd>
            <Cifra valor={`${formatNumeroCL(chile.tpm, 2)}%`} fuente={chile.fuente} />
          </dd>
        </div>
        <div>
          <dt>IPC 12m</dt>
          <dd>
            <Cifra valor={`${formatNumeroCL(chile.ipc_12m, 1)}%`} fuente={chile.fuente} />
          </dd>
        </div>
      </dl>
    </div>
  );
}
