/** @odoo-module **/

import { Component, useState, onWillStart } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";

class ItParcDashboard extends Component {
    static template = "it_parc.Dashboard";
    static props = {};

    setup() {
        this.orm = useService("orm");
        this.action = useService("action");

        this.state = useState({
            loaded: false,
            total_equipements: 0,
            equipements_affectes: 0,
            equipements_maintenance: 0,
            contrats_expirant: 0,
            garanties_expirantes: 0,
            total_cout_maintenance: 0,
            chart_data: [],
        });

        onWillStart(async () => {
            await this._loadData();
        });
    }

    async _loadData() {
        try {
            const data = await this.orm.call("it.equipement", "get_dashboard_data", []);
            Object.assign(this.state, data, { loaded: true });
        } catch (e) {
            console.error("IT Parc Dashboard: erreur chargement données", e);
            this.state.loaded = true;
        }
    }

    formatNumber(val) {
        if (val === undefined || val === null) return "0";
        return new Intl.NumberFormat("fr-FR").format(val);
    }

    get chartMaxHeight() {
        return 180;
    }

    get chartItems() {
        return this.state.chart_data || [];
    }

    get svgWidth() {
        const n = this.chartItems.length;
        return Math.max(n * 110 + 60, 400);
    }

    barX(index) {
        return index * 110 + 40;
    }

    barY(item) {
        return this.chartMaxHeight + 20 - (item.height || 0);
    }

    labelX(index) {
        return this.barX(index) + 40;
    }

    openEquipements(state) {
        const domain = state ? [["state", "=", state]] : [];
        this.action.doAction({
            type: "ir.actions.act_window",
            name: "Équipements",
            res_model: "it.equipement",
            view_mode: "list,form",
            domain: domain,
            target: "current",
        });
    }

    openAlertes() {
        this.action.doAction({
            type: "ir.actions.act_window",
            name: "Alertes actives",
            res_model: "it.alerte",
            view_mode: "list,form",
            domain: [["state", "=", "active"]],
            target: "current",
        });
    }

    openContrats() {
        this.action.doAction({
            type: "ir.actions.act_window",
            name: "Contrats expirant bientôt",
            res_model: "it.contrat",
            view_mode: "list,form",
            domain: [["state", "=", "actif"]],
            target: "current",
        });
    }
}

registry.category("actions").add("it_parc_dashboard", ItParcDashboard);
