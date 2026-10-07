import React, { useState } from 'react'

const PHONE = '919259599151'
const OPTIONS = [
  'Electrical repair or installation',
  'CCTV installation or repair',
  'Networking / Wi-Fi',
  'Electrical inspection / commercial work',
  'Other technical service',
]

/**
 * A contact request, NOT a reservation. No details are submitted to our server.
 * The visitor chooses whether to send the prepared message from WhatsApp.
 */
export default function OfflineInquiry({ initialService, openPrivacy }: {
  initialService?: string
  openPrivacy: () => void
}) {
  const [service, setService] = useState(initialService || OPTIONS[0])
  const [issue, setIssue] = useState('')
  const [area, setArea] = useState('')
  const [mode, setMode] = useState<'service_only' | 'with_materials'>('service_only')
  const [acknowledged, setAcknowledged] = useState(false)

  function submit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (!acknowledged || issue.trim().length < 10) return

    const details = [
      'Hello Shiva Enterprises, I would like to request a service consultation.',
      `Service: ${service}`,
      `Requirement: ${issue.trim()}`,
      `Area: ${area.trim() || 'To be confirmed'}`,
      `Type: ${mode === 'with_materials' ? 'Service + material estimate' : 'Service only'}`,
      'Please confirm availability, scope and charges before scheduling.'
    ].join('\n')
    // WhatsApp opens with a draft. Nothing is submitted until the visitor sends it.
    window.location.assign(`https://wa.me/${PHONE}?text=${encodeURIComponent(details)}`)
  }

  return <section className="form-section inquiry-page">
    <div className="form-intro">
      <small className="eyebrow">PERSONAL ASSISTANCE</small>
      <h1>Request a service consultation</h1>
      <p>Online account bookings are not available right now. Send an enquiry on WhatsApp, or call us directly.</p>
      <div className="charge-summary">
        <strong>This is an enquiry, not a confirmed booking.</strong>
        <span>Service availability, inspection charges, taxes and any materials will be confirmed before work starts.</span>
        <span>Please do not include OTPs, passwords, Aadhaar numbers or payment details in your message.</span>
      </div>
      <a className="secondary" href="tel:+919259599151">Call +91 9259599151</a>
    </div>
    <form className="form-card wide" onSubmit={submit}>
      <label>Service needed
        <select value={service} onChange={e => setService(e.target.value)}>
          {!OPTIONS.includes(service) && <option value={service}>{service}</option>}
          {OPTIONS.map(item => <option key={item} value={item}>{item}</option>)}
        </select>
      </label>
      <label>Tell us the problem
        <textarea value={issue} onChange={e => setIssue(e.target.value)} required minLength={10} maxLength={500}
          rows={4} placeholder="Example: Two CCTV cameras have stopped recording. Please inspect the DVR."/>
      </label>
      <label>Area in Dehradun (optional)
        <input value={area} onChange={e => setArea(e.target.value)} maxLength={80}
          placeholder="Neighbourhood only; no full address needed"/>
      </label>
      <label>Service type
        <select value={mode} onChange={e => setMode(e.target.value as typeof mode)}>
          <option value="service_only">Service only</option>
          <option value="with_materials">Service + materials (estimate required)</option>
        </select>
      </label>
      <label className="check disclosure-check">
        <input type="checkbox" checked={acknowledged} onChange={e => setAcknowledged(e.target.checked)} required />
        <span>I understand this will open WhatsApp with a draft message; I must press Send there. It does not create a booking or charge me. I have read the <button type="button" className="inline-link" onClick={openPrivacy}>privacy information</button>.</span>
      </label>
      <button className="primary full" type="submit" disabled={!acknowledged || issue.trim().length < 10}>Continue to WhatsApp →</button>
      <p className="muted">Your form details remain in this browser until you choose to open WhatsApp. WhatsApp has its own privacy practices.</p>
    </form>
  </section>
}
