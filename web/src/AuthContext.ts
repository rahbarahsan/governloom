import { createContext } from "react";
export type Operator = { id: string; username: string; role: "admin" | "operator" | "reviewer" | "viewer"; application_ids: string[] };
export const AuthContext = createContext<Operator | null>(null);
