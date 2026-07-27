export function friendlyErrorMessage(error: unknown, fallback: string): string {
  const rawMessage = error instanceof Error ? error.message : "";
  const message = rawMessage.toLowerCase();

  if (message.includes("failed to fetch") || message.includes("no es posible conectar")) {
    return "No pude conectar con el servidor. Revisa que la API este abierta en http://127.0.0.1:8000 y vuelve a intentar.";
  }

  if (
    message.includes("ya existe un recurso") ||
    message.includes("duplicate key") ||
    message.includes("unique constraint")
  ) {
    return "Ese codigo ya esta usado por otro recurso. Si querias cambiar el stock minimo, editalo en la tabla de recursos registrados. Si es un recurso nuevo, usa otro codigo.";
  }

  if (message.includes("ya existe una formula")) {
    return "Ya existe una formula con ese nombre y esa version. Crea una nueva version o cambia el nombre antes de guardar.";
  }

  if (message.includes("debe sumar 100")) {
    return "La formula todavia no cierra: los porcentajes deben sumar exactamente 100%. Ajusta los ingredientes y vuelve a guardar.";
  }

  if (message.includes("stock insuficiente")) {
    if (message.includes("venta")) {
      return rawMessage;
    }
    return "No hay stock suficiente para crear ese lote. Revisa las materias primas necesarias o carga una compra/ajuste de stock antes de producir.";
  }

  if (message.includes("formula no encontrada")) {
    return "No encuentro esa formula. Actualiza la pantalla y selecciona una formula disponible.";
  }

  if (message.includes("recurso no encontrado")) {
    return "No encuentro ese recurso. Actualiza la pantalla y vuelve a intentarlo.";
  }

  if (message.includes("field required") || message.includes("input should")) {
    return "Falta completar algun dato obligatorio o hay un valor con formato incorrecto. Revisa los campos marcados y vuelve a intentar.";
  }

  return rawMessage || fallback;
}
