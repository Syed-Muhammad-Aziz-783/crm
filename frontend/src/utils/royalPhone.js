// Royal: one phone field only.
// Layouts may hold Mobile No, Phone, or both. Show one field named Phone:
// if both exist keep Phone and drop Mobile No, if only Mobile No exists show it as Phone.
// The server keeps both stored values equal.
export function royalPhoneFields(fields = []) {
  const hasPhone = fields.some((f) => f.fieldname === 'phone')
  return fields
    .filter((f) => !(hasPhone && f.fieldname === 'mobile_no'))
    .map((f) =>
      f.fieldname === 'mobile_no'
        ? { ...f, fieldname: 'phone', label: 'Phone' }
        : f,
    )
}
