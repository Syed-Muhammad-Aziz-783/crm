// Royal: ERPNext desk tweaks.
// 1. Small "Copy" button on every phone / mobile field.
// 2. One phone field only: hide Mobile No when a Phone field exists, else show it as "Phone".
// Display only. Stored data is not changed here.
(function () {
	function copyText(text) {
		text = (text || "").toString().trim();
		if (!text) return;
		if (frappe.utils && frappe.utils.copy_to_clipboard) {
			frappe.utils.copy_to_clipboard(text);
			return;
		}
		const el = document.createElement("textarea");
		el.value = text;
		document.body.appendChild(el);
		el.select();
		document.execCommand("copy");
		document.body.removeChild(el);
		frappe.show_alert({ message: __("Copied"), indicator: "green" });
	}

	function is_phone_field(df) {
		if (!df) return false;
		return (
			df.options === "Phone" ||
			df.fieldtype === "Phone" ||
			["phone", "mobile_no", "mobile", "phone_no", "cell_number"].includes(df.fieldname)
		);
	}

	function add_copy_button(control) {
		if (!control || !control.$wrapper || !is_phone_field(control.df)) return;
		if (control.$wrapper.find(".royal-copy-btn").length) return;
		const $btn = $(
			'<button type="button" class="btn btn-xs btn-default royal-copy-btn" title="' +
				__("Copy number") +
				'">' +
				__("Copy") +
				"</button>"
		);
		$btn.on("click", function (e) {
			e.preventDefault();
			e.stopPropagation();
			const value =
				(control.get_value && control.get_value()) ||
				control.value ||
				(control.$input && control.$input.val());
			copyText(value);
		});
		const $target = control.$wrapper.find(".control-input-wrapper").first();
		($target.length ? $target : control.$wrapper).append($btn);
	}

	function patch_controls() {
		const ctor = frappe.ui && frappe.ui.form && frappe.ui.form.ControlData;
		if (!ctor || ctor.prototype.__royal_patched) return false;
		const original = ctor.prototype.make_input;
		ctor.prototype.make_input = function () {
			const result = original.apply(this, arguments);
			try {
				add_copy_button(this);
			} catch (e) {
				/* never break a form because of a copy button */
			}
			return result;
		};
		ctor.prototype.__royal_patched = true;

		const phone = frappe.ui.form.ControlPhone;
		if (phone && Object.prototype.hasOwnProperty.call(phone.prototype, "make_input")) {
			const original_phone = phone.prototype.make_input;
			phone.prototype.make_input = function () {
				const result = original_phone.apply(this, arguments);
				try {
					add_copy_button(this);
				} catch (e) {}
				return result;
			};
		}
		return true;
	}

	function one_phone_field(frm) {
		if (!frm || !frm.fields_dict || !frm.fields_dict.mobile_no) return;
		try {
			if (frm.fields_dict.phone) {
				frm.set_df_property("mobile_no", "hidden", 1);
			} else {
				frm.set_df_property("mobile_no", "label", __("Phone"));
			}
		} catch (e) {}
	}

	$(document).on("form-refresh", function (e, frm) {
		one_phone_field(frm);
	});

	$(function () {
		if (!patch_controls()) {
			// controls load a moment later on some pages
			const timer = setInterval(function () {
				if (patch_controls()) clearInterval(timer);
			}, 500);
			setTimeout(function () {
				clearInterval(timer);
			}, 15000);
		}
	});

	// Royal: live sync in the desk (ERPNext, HRMS and every other app).
	// The open list or form quietly refreshes when something changes, when you come
	// back to the tab, and never while you are typing or have unsaved edits.
	function quiet_refresh() {
		try {
			if (document.visibilityState !== "visible") return;
			var a = document.activeElement;
			if (a && (/^(INPUT|TEXTAREA|SELECT)$/.test(a.tagName) || a.isContentEditable)) return;
			if (window.cur_frm && cur_frm.doc && !cur_frm.is_new() && !cur_frm.is_dirty()) {
				cur_frm.reload_doc();
			} else if (window.cur_list && cur_list.refresh && !window.cur_frm) {
				cur_list.refresh();
			}
		} catch (e) {}
	}
	var debounced_refresh = frappe.utils.debounce(quiet_refresh, 800);

	function start_live_sync() {
		if (!frappe.realtime || !frappe.realtime.on) return false;
		frappe.realtime.on("list_update", function (d) {
			if (window.cur_list && d && cur_list.doctype === d.doctype) debounced_refresh();
		});
		frappe.realtime.on("doc_update", function (d) {
			if (
				window.cur_frm &&
				d &&
				cur_frm.doctype === d.doctype &&
				cur_frm.docname === d.name &&
				d.modified !== cur_frm.doc.modified
			) {
				debounced_refresh();
			}
		});
		document.addEventListener("visibilitychange", debounced_refresh);
		return true;
	}
	$(function () {
		if (!start_live_sync()) setTimeout(start_live_sync, 3000);
	});
})();

// Royal: desk apps screen tiles that point to our own site (for example Frappe CRM at /crm)
// open in the SAME tab. Frappe adds target="_blank" to every External tile; we remove it only
// when the link stays on this site. Links to other sites still open in a new tab.
(function () {
	function same_tab_for_own_site() {
		try {
			var tiles = document.querySelectorAll('a.desktop-icon[target="_blank"]');
			for (var i = 0; i < tiles.length; i++) {
				var href = tiles[i].getAttribute("href") || "";
				if (href.indexOf(window.location.origin + "/") === 0 || href.charAt(0) === "/") {
					tiles[i].removeAttribute("target");
					tiles[i].removeAttribute("rel");
				}
			}
		} catch (e) {
			/* never break the desk because of this */
		}
	}
	var queued = false;
	function schedule() {
		if (queued) return;
		queued = true;
		setTimeout(function () {
			queued = false;
			same_tab_for_own_site();
		}, 50);
	}
	function start() {
		if (!document.body) return setTimeout(start, 200);
		same_tab_for_own_site();
		new MutationObserver(schedule).observe(document.body, { childList: true, subtree: true });
	}
	start();
})();
