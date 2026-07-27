import type { Metadata } from "next";
import { AuthProvider } from "@/lib/auth";
import "./styles.css";

export const metadata: Metadata = {
  title: "Eter ERP",
  description: "Gestion operativa para blends, produccion e inventario.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="es">
      <body>
        <AuthProvider>{children}</AuthProvider>
      </body>
    </html>
  );
}
